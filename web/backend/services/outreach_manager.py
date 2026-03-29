"""Оркестратор рассылок — единственный владелец Telethon-сессий.

Импортирует core-сервисы бота через sys.path и управляет полным
жизненным циклом кампаний: создание → запуск → пауза → отмена.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from core.config import settings

logger = logging.getLogger(__name__)


def _ensure_bot_importable() -> None:
    """Добавляет project root в sys.path для импорта bot.* пакетов."""
    import os
    root = str(settings.project_root)
    if root not in sys.path:
        sys.path.insert(0, root)
        logger.info(f"Added {root} to sys.path")
    # bot.utils.config требует BOT_TOKEN — web backend не использует aiogram,
    # поэтому ставим заглушку чтобы import не падал
    if not os.environ.get("BOT_TOKEN"):
        os.environ["BOT_TOKEN"] = "unused-by-web-backend"


# Lazy imports — вызываются после _ensure_bot_importable()
def _import_bot_modules():
    """Ленивый импорт модулей бота."""
    from bot.services.account_pool import AccountPool, AccountInfo
    from bot.services.outreach import (
        OutreachService,
        active_outreach,
        add_service,
        remove_service,
        _clients_with_handler,
    )
    from bot.services.ai_sales import AISalesEngine
    from bot.services.outreach_storage import OutreachStorage
    from bot.models.outreach import OutreachCampaign, OutreachRecipient

    return {
        "AccountPool": AccountPool,
        "AccountInfo": AccountInfo,
        "OutreachService": OutreachService,
        "active_outreach": active_outreach,
        "add_service": add_service,
        "remove_service": remove_service,
        "clients_with_handler": _clients_with_handler,
        "AISalesEngine": AISalesEngine,
        "OutreachStorage": OutreachStorage,
        "OutreachCampaign": OutreachCampaign,
        "OutreachRecipient": OutreachRecipient,
    }


class OutreachManager:
    """Центральный оркестратор рассылок.

    Владеет:
    - AccountPool (Telethon-клиенты)
    - Активными OutreachService (по одному на кампанию)
    - Pending OTP-авторизациями
    """

    def __init__(self):
        self._bot = None  # Lazy-loaded bot modules dict
        self._pool = None  # AccountPool instance
        self._ai_engine = None  # AISalesEngine instance
        self._tg_bot = None  # aiogram Bot for notifications
        self._active_services: dict[str, object] = {}  # campaign_id → OutreachService
        self._pending_auth: dict[str, object] = {}  # phone → TelegramClient awaiting OTP
        self._campaign_tasks: dict[str, asyncio.Task] = {}  # campaign_id → send task
        self._started = False

    def _bot_modules(self):
        """Возвращает кеш bot modules."""
        if self._bot is None:
            _ensure_bot_importable()
            self._bot = _import_bot_modules()
        return self._bot

    @property
    def pool(self):
        """AccountPool instance."""
        return self._pool

    @property
    def ai_engine(self):
        """AISalesEngine instance."""
        return self._ai_engine

    # ─── Startup / Shutdown ───

    async def startup(self) -> None:
        """Инициализация при старте web backend."""
        if self._started:
            return

        bot = self._bot_modules()

        # Патчим bot модули для работы с DB вместо JSON
        import bot.services.account_pool as _ap_mod
        import bot.services.outreach_storage as _os_mod
        _ap_mod.ACCOUNTS_FILE = settings.project_root / "data" / "telethon_accounts.json"

        # Подменяем OutreachStorage на DB-backed версию
        from services.db_storage import DbOutreachStorage, set_db_path, set_on_save_callback
        set_db_path(settings.db_path)
        _os_mod.OutreachStorage = DbOutreachStorage

        # Патчим также в outreach.py (он делает from ... import OutreachStorage)
        import bot.services.outreach as _outreach_mod
        _outreach_mod.OutreachStorage = DbOutreachStorage

        # WebSocket уведомления при save()
        from services.ws_manager import ws_manager
        set_on_save_callback(ws_manager.notify_campaign_saved)

        logger.info(f"OutreachStorage → DbOutreachStorage (db={settings.db_path})")

        # Создаём AccountPool и подключаем все аккаунты
        # Подменяем _save/_load на DB-версии
        from services.db_account_storage import db_save_accounts, db_load_accounts
        self._pool = bot["AccountPool"]()
        self._pool._save = lambda: db_save_accounts(self._pool.accounts, settings.db_path)
        self._pool._load = lambda: db_load_accounts(self._pool, settings.db_path)
        connected = await self._pool.connect_all(session_dir=str(settings.project_root))
        logger.info(f"AccountPool: {connected} account(s) connected")

        # Регистрируем наш pool как глобальный — OutreachService использует get_account_pool()
        _ap_mod._pool = self._pool

        # Создаём AISalesEngine
        if settings.openrouter_api_key:
            self._ai_engine = bot["AISalesEngine"](
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model,
            )
            logger.info(f"AISalesEngine ready (model={settings.openrouter_model})")
        else:
            logger.warning("OPENROUTER_API_KEY not set — AI responses disabled")

        # Создаём aiogram Bot для уведомлений
        if settings.telegram_bot_token:
            try:
                from aiogram import Bot
                self._tg_bot = Bot(token=settings.telegram_bot_token)
                logger.info("Telegram bot initialized for notifications")
            except Exception as e:
                logger.warning(f"Failed to init Telegram bot: {e}")
        else:
            logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram notifications disabled")

        # Восстанавливаем активные кампании (используем DB-backed storage напрямую)
        storage = DbOutreachStorage()
        active_campaigns = storage.load_all_active()
        for campaign in active_campaigns:
            try:
                await self._restore_campaign(campaign)
            except Exception as e:
                logger.error(f"Failed to restore campaign {campaign.campaign_id}: {e}")

        self._started = True
        logger.info(f"OutreachManager started, restored {len(active_campaigns)} campaign(s)")

    async def shutdown(self) -> None:
        """Остановка при завершении web backend."""
        # Отменяем все задачи рассылки
        for task in self._campaign_tasks.values():
            if not task.done():
                task.cancel()
        self._campaign_tasks.clear()

        # Закрываем AI engine
        if self._ai_engine:
            await self._ai_engine.close()

        # Закрываем aiogram Bot
        if self._tg_bot:
            await self._tg_bot.session.close()

        # Отключаем Telethon-клиенты
        if self._pool:
            await self._pool.disconnect_all()

        # Отключаем pending OTP клиенты
        for client in self._pending_auth.values():
            try:
                await client.disconnect()
            except Exception:
                pass
        self._pending_auth.clear()

        self._started = False
        logger.info("OutreachManager stopped")

    # ─── Notifications ───

    def _make_notify_callback(self, user_id: int):
        """Создаёт callback для уведомлений через Telegram Bot API."""
        tg_bot = self._tg_bot
        if not tg_bot:
            return None

        from bot.utils.messages import Messages

        async def on_notify(event_type: str, **kwargs):
            try:
                camp = kwargs.get("campaign")
                recipient = kwargs.get("recipient")
                msg_text = None
                notify_managers = False

                if event_type == "first_reply":
                    msg_text = Messages.outreach_first_reply(
                        recipient, kwargs.get("lead_message", "")
                    )
                    notify_managers = True
                elif event_type in ("warm_lead", "warm_lead_reply"):
                    msg_text = Messages.outreach_warm_lead(recipient)
                    notify_managers = True
                elif event_type == "referral":
                    msg_text = Messages.outreach_referral(
                        recipient,
                        referral_name=kwargs.get("referral_name"),
                        referral_phone=kwargs.get("referral_phone"),
                        referral_found=kwargs.get("referral_found"),
                    )
                    notify_managers = True
                elif event_type == "sending_complete":
                    msg_text = (
                        f"✅ <b>Рассылка завершена!</b>\n\n"
                        f"Отправлено: {camp.sent_count}\n"
                        f"Нет в Telegram: {camp.not_found_count}\n\n"
                        f"AI слушает ответы и будет пинговать при игноре."
                    )
                elif event_type == "daily_limit":
                    msg_text = "⚠️ Достигнут дневной лимит рассылки. Кампания продолжится завтра."

                if not msg_text:
                    return

                # Отправляем владельцу
                try:
                    await tg_bot.send_message(user_id, msg_text, parse_mode="HTML")
                except Exception as e:
                    logger.warning(f"Can't notify user {user_id}: {e}")

                # Отправляем менеджерам
                if notify_managers and camp and camp.manager_ids:
                    for manager_id in camp.manager_ids:
                        try:
                            await tg_bot.send_message(manager_id, msg_text, parse_mode="HTML")
                        except Exception as e:
                            logger.warning(f"Can't notify manager {manager_id}: {e}")

            except Exception as e:
                logger.error(f"Notify callback error: {e}")

        return on_notify

    # ─── Campaign Lifecycle ───

    async def launch_campaign(self, campaign_id: str) -> dict:
        """Запускает кампанию (pending → sending)."""
        bot = self._bot_modules()

        # Ищем кампанию в DB
        from services.db_storage import DbOutreachStorage
        storage = DbOutreachStorage()
        campaign = storage.load(0, campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        if campaign.status not in ("pending",):
            raise ValueError(f"Cannot launch campaign with status '{campaign.status}'")

        if not self._pool or not self._pool.get_active_accounts():
            raise RuntimeError("Нет подключённых аккаунтов")

        if not self._ai_engine:
            raise RuntimeError("AI engine не настроен (нет OPENROUTER_API_KEY)")

        # Создаём OutreachService
        service = bot["OutreachService"](ai_engine=self._ai_engine)
        # Per-campaign working hours override
        wh_start = getattr(campaign, "work_hour_start", None)
        wh_end = getattr(campaign, "work_hour_end", None)
        if wh_start is not None:
            service._work_hour_start = wh_start
        if wh_end is not None:
            service._work_hour_end = wh_end
        notify_cb = self._make_notify_callback(campaign.user_id)
        if notify_cb:
            service.set_notify_callback(notify_cb)
        self._active_services[campaign_id] = service

        # Регистрируем в глобальном реестре бота
        bot["add_service"](campaign.user_id, campaign_id, service)

        # Обновляем статус в DB сразу
        self._update_campaign_status_in_db(campaign_id, "sending", allowed=("pending",))

        # Запускаем в фоне
        task = asyncio.create_task(
            self._run_campaign(service, campaign, bot)
        )
        self._campaign_tasks[campaign_id] = task

        return {
            "campaign_id": campaign_id,
            "status": "sending",
            "message": f"Кампания запущена ({len(campaign.recipients)} получателей)",
        }

    async def _run_campaign(self, service, campaign, bot) -> None:
        """Фоновая задача рассылки."""
        try:
            await service.start_campaign(campaign)
        except Exception as e:
            logger.error(f"Campaign {campaign.campaign_id} error: {e}")
        finally:
            # После завершения рассылки (sending → listening) — сервис остаётся
            # для прослушивания ответов. Не удаляем из active_services.
            logger.info(f"Campaign {campaign.campaign_id} send loop finished, status={campaign.status}")

    async def _restore_campaign(self, campaign) -> None:
        """Восстанавливает кампанию после рестарта."""
        bot = self._bot_modules()

        if not self._ai_engine:
            logger.warning(f"Cannot restore campaign {campaign.campaign_id}: no AI engine")
            return

        service = bot["OutreachService"](ai_engine=self._ai_engine)
        # Per-campaign working hours override
        wh_start = getattr(campaign, "work_hour_start", None)
        wh_end = getattr(campaign, "work_hour_end", None)
        if wh_start is not None:
            service._work_hour_start = wh_start
        if wh_end is not None:
            service._work_hour_end = wh_end
        notify_cb = self._make_notify_callback(campaign.user_id)
        if notify_cb:
            service.set_notify_callback(notify_cb)
        self._active_services[campaign.campaign_id] = service
        bot["add_service"](campaign.user_id, campaign.campaign_id, service)

        if campaign.status == "sending":
            task = asyncio.create_task(
                self._run_campaign_resume(service, campaign)
            )
            self._campaign_tasks[campaign.campaign_id] = task
        elif campaign.status in ("listening", "paused"):
            # Восстанавливаем listener + ping
            service._campaign = campaign
            await service.start_listener()
            service._ping_task = asyncio.create_task(service._ping_loop())
            await service.retry_unanswered()
            if campaign.status == "paused":
                service.pause()

        logger.info(f"Restored campaign {campaign.campaign_id} (status={campaign.status})")

    async def _run_campaign_resume(self, service, campaign) -> None:
        """Возобновление рассылки после рестарта."""
        try:
            await service.start_campaign(campaign, resume=True)
        except Exception as e:
            logger.error(f"Campaign resume {campaign.campaign_id} error: {e}")

    async def pause_campaign(self, campaign_id: str) -> dict:
        """Ставит кампанию на паузу."""
        service = self._active_services.get(campaign_id)
        if service and service.campaign:
            if service.campaign.status not in ("sending", "listening", "paused"):
                raise ValueError(f"Cannot pause campaign with status '{service.campaign.status}'")
            if service.campaign.status != "paused":
                service.pause()

        # Всегда синхронизируем DB
        self._update_campaign_status_in_db(
            campaign_id, "paused", allowed=("sending", "listening", "paused"),
        )

        return {
            "campaign_id": campaign_id,
            "status": "paused",
            "message": "Кампания приостановлена",
        }

    async def resume_campaign(self, campaign_id: str) -> dict:
        """Возобновляет кампанию после паузы."""
        service = self._active_services.get(campaign_id)
        if service and service.campaign:
            if service.campaign.status not in ("paused", "listening"):
                raise ValueError(f"Cannot resume campaign with status '{service.campaign.status}'")
            if service.campaign.status == "paused":
                service.resume()
            new_status = service.campaign.status
        else:
            new_status = "listening"

        # Всегда синхронизируем DB
        self._update_campaign_status_in_db(
            campaign_id, new_status, allowed=("paused", "listening", "sending"),
        )

        return {
            "campaign_id": campaign_id,
            "status": new_status,
            "message": "Кампания возобновлена",
        }

    async def cancel_campaign(self, campaign_id: str) -> dict:
        """Отменяет кампанию."""
        bot = self._bot_modules()

        # Сначала обновляем статус в DB (до service.cancel() который может удалить)
        try:
            self._update_campaign_status_in_db(campaign_id, "cancelled")
        except ValueError:
            pass  # Кампания уже удалена — ок

        service = self._active_services.get(campaign_id)
        if service:
            campaign = service.campaign
            user_id = campaign.user_id if campaign else 0

            # Отменяем фоновую задачу
            task = self._campaign_tasks.pop(campaign_id, None)
            if task and not task.done():
                task.cancel()

            # Отменяем сервис (удаляет контакты)
            # Подменяем delete чтобы не удалял из DB (мы уже поставили cancelled)
            original_delete = service._storage.delete
            service._storage.delete = lambda *a, **kw: None
            await service.cancel()
            service._storage.delete = original_delete

            # Убираем из реестров
            self._active_services.pop(campaign_id, None)
            bot["remove_service"](user_id, campaign_id)

        return {
            "campaign_id": campaign_id,
            "status": "cancelled",
            "message": "Кампания отменена",
        }

    def _update_campaign_status_in_db(
        self, campaign_id: str, new_status: str, allowed: tuple[str, ...] | None = None,
    ) -> None:
        """Обновляет статус кампании напрямую в DB (когда нет активного сервиса)."""
        import sqlite3
        conn = sqlite3.connect(str(settings.db_path))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT status FROM campaigns WHERE campaign_id=?", (campaign_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Campaign {campaign_id} not found")
            if allowed and row["status"] not in allowed:
                raise ValueError(
                    f"Cannot change campaign from '{row['status']}' to '{new_status}'"
                )
            conn.execute(
                "UPDATE campaigns SET status=?, updated_at=datetime('now') WHERE campaign_id=?",
                (new_status, campaign_id),
            )
            conn.commit()
            logger.info(f"Campaign {campaign_id} status → {new_status} (DB direct)")
        finally:
            conn.close()

    def get_campaign_status(self, campaign_id: str) -> Optional[dict]:
        """Статус активной кампании."""
        service = self._active_services.get(campaign_id)
        if not service or not service.campaign:
            return None
        c = service.campaign
        return {
            "campaign_id": c.campaign_id,
            "status": c.status,
            "sent_count": c.sent_count,
            "warm_count": c.warm_count,
            "rejected_count": c.rejected_count,
            "not_found_count": c.not_found_count,
            "recipients_total": len(c.recipients),
        }

    # ─── Account Management ───

    def get_accounts(self) -> list[dict]:
        """Список всех аккаунтов."""
        if not self._pool:
            return []
        result = []
        for a in self._pool.accounts:
            result.append({
                "phone": a.phone,
                "phone_masked": a.phone[:4] + "****" + a.phone[-2:] if len(a.phone) > 6 else a.phone,
                "active": a.active,
                "connected": a.phone in self._pool.clients,
                "session_name": a.session_name,
                "sent_today": self._pool.sent_today.get(a.phone, 0),
                "daily_limit": settings.outreach_daily_limit,
            })
        return result

    async def add_account(self, phone: str, api_id: int, api_hash: str) -> dict:
        """Добавляет новый аккаунт (без подключения)."""
        if not self._pool:
            raise RuntimeError("OutreachManager not started")

        account = self._pool.add_account(phone, api_id, api_hash)
        return {
            "phone": account.phone,
            "session_name": account.session_name,
            "active": account.active,
            "connected": False,
            "message": f"Аккаунт {phone} добавлен. Используйте /connect для авторизации.",
        }

    async def remove_account(self, phone: str) -> bool:
        """Удаляет аккаунт из пула."""
        if not self._pool:
            return False

        # Отключаем клиент если подключён
        client = self._pool.clients.get(phone)
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass

        return self._pool.remove_account(phone)

    async def toggle_account(self, phone: str) -> dict:
        """Вкл/выкл аккаунт."""
        if not self._pool:
            raise RuntimeError("OutreachManager not started")

        for a in self._pool.accounts:
            if a.phone == phone:
                a.active = not a.active
                self._pool._save()
                return {
                    "phone": phone,
                    "active": a.active,
                    "message": f"Аккаунт {'активирован' if a.active else 'деактивирован'}",
                }
        raise ValueError(f"Аккаунт {phone} не найден")

    # ─── OTP Flow ───

    async def start_auth(self, phone: str) -> dict:
        """Шаг 1: Начинает OTP-авторизацию → отправляет код на телефон."""
        if not self._pool:
            raise RuntimeError("OutreachManager not started")

        # Ищем аккаунт
        account = None
        for a in self._pool.accounts:
            if a.phone == phone:
                account = a
                break
        if not account:
            raise ValueError(f"Аккаунт {phone} не найден")

        # Создаём клиент (не start(), только connect + send_code_request)
        # Сессия должна лежать в project root, а не в web/backend/
        from telethon import TelegramClient
        session_path = str(settings.project_root / account.session_name)
        client = TelegramClient(
            session_path,
            account.api_id,
            account.api_hash,
            lang_code="ru",
            system_lang_code="ru-RU",
        )
        await client.connect()

        result = await client.send_code_request(phone)
        self._pending_auth[phone] = client

        return {
            "phone_code_hash": result.phone_code_hash,
            "message": f"Код отправлен на {phone}",
        }

    async def verify_auth(
        self,
        phone: str,
        code: str,
        phone_code_hash: str,
        password: Optional[str] = None,
    ) -> dict:
        """Шаг 2: Верифицирует OTP-код (+ опционально 2FA пароль)."""
        client = self._pending_auth.get(phone)
        if not client:
            raise ValueError(f"Нет ожидающей авторизации для {phone}")

        from telethon.errors import SessionPasswordNeededError

        try:
            if password:
                await client.sign_in(password=password)
            else:
                await client.sign_in(phone, code, phone_code_hash=phone_code_hash)

            # Успех — сохраняем клиент в пул
            self._pool.clients[phone] = client
            self._pool.sent_today[phone] = 0
            self._pending_auth.pop(phone, None)

            logger.info(f"Account {phone} authorized and connected")
            return {
                "success": True,
                "needs_2fa": False,
                "message": f"Аккаунт {phone} подключён",
            }

        except SessionPasswordNeededError:
            return {
                "success": False,
                "needs_2fa": True,
                "message": "Требуется пароль двухфакторной аутентификации",
            }

        except Exception as e:
            # Ошибка — отключаем клиент
            self._pending_auth.pop(phone, None)
            try:
                await client.disconnect()
            except Exception:
                pass
            raise ValueError(f"Ошибка авторизации: {e}")
