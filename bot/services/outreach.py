"""Ядро AI-продажника: рассылка + слушатель ответов + автопинг."""

import asyncio
import logging
import random
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Awaitable

from telethon import events
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from telethon.errors import FloodWaitError

from bot.models.outreach import OutreachCampaign, OutreachRecipient
from bot.services.ai_sales import AISalesEngine
from bot.services.sherlock_client import get_sherlock_client, is_telethon_configured
from bot.utils.config import settings

logger = logging.getLogger(__name__)

# Московское время UTC+3
MSK_OFFSET = timedelta(hours=3)


def normalize_phone(phone: str) -> str:
    """Нормализует телефон в формат +7XXXXXXXXXX."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if not digits.startswith("7"):
        digits = "7" + digits
    return "+" + digits


def render_first_message(offer: str, recipient: OutreachRecipient) -> str:
    """Формирует первое сообщение для лида."""
    name = recipient.contact_name or "коллега"
    company = recipient.company_name
    return f"Здравствуйте, {name}! Пишу вам по поводу {company}.\n\n\n{offer}"


class OutreachService:
    """Сервис AI-продажника."""

    def __init__(self, ai_engine: AISalesEngine):
        self.ai_engine = ai_engine
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        self._cancelled = False
        self._campaign: Optional[OutreachCampaign] = None
        self._listener_handler = None
        self._ping_task: Optional[asyncio.Task] = None
        self._notify_callback: Optional[Callable] = None

    def set_notify_callback(self, callback: Callable[..., Awaitable]) -> None:
        """Устанавливает callback для уведомлений (тёплый лид, прогресс и т.д.)."""
        self._notify_callback = callback

    async def _notify(self, event_type: str, **kwargs) -> None:
        """Отправляет уведомление через callback."""
        if self._notify_callback:
            try:
                await self._notify_callback(event_type, **kwargs)
            except Exception as e:
                logger.error(f"Notify callback error: {e}")

    # ─── Фаза 1: Рассылка первых сообщений ───

    async def start_campaign(
        self,
        campaign: OutreachCampaign,
        progress_callback: Optional[Callable[..., Awaitable]] = None,
    ) -> None:
        """Запускает фазу 1: рассылка первых сообщений."""
        if not is_telethon_configured():
            raise RuntimeError("Telethon не настроен. Укажите TELETHON_API_ID/HASH/PHONE в .env")

        self._campaign = campaign
        self._cancelled = False
        self._pause_event.set()
        campaign.status = "sending"

        client_wrapper = await get_sherlock_client()
        client = client_wrapper.client

        # Запускаем listener СРАЗУ, до рассылки — чтобы ловить быстрые ответы
        await self.start_listener()
        self._ping_task = asyncio.create_task(self._ping_loop())

        sent_today = 0

        for i, recipient in enumerate(campaign.recipients):
            if self._cancelled:
                break

            # Проверка паузы
            await self._pause_event.wait()

            # Дневной лимит
            if sent_today >= settings.outreach_daily_limit:
                logger.warning("Daily limit reached")
                await self._notify("daily_limit", campaign=campaign)
                break

            phone = normalize_phone(recipient.phone)

            try:
                # Добавляем в контакты для resolve
                contact = InputPhoneContact(
                    client_id=0,
                    phone=phone,
                    first_name=recipient.contact_name or recipient.company_name,
                    last_name="",
                )
                result = await client(ImportContactsRequest([contact]))

                if not result.users:
                    recipient.status = "not_found"
                    campaign.not_found_count += 1
                    logger.info(f"Phone {phone} not in Telegram")
                    continue

                user = result.users[0]
                recipient.telegram_user_id = user.id

                # Формируем и отправляем первое сообщение
                message_text = render_first_message(campaign.offer, recipient)
                await client.send_message(user.id, message_text)

                recipient.status = "sent"
                recipient.last_message_at = datetime.now(timezone.utc)
                recipient.conversation_history.append({
                    "role": "assistant",
                    "content": message_text,
                })
                campaign.sent_count += 1
                sent_today += 1

                logger.info(f"Sent to {phone} ({recipient.company_name})")

                # Прогресс
                if progress_callback:
                    await progress_callback(i + 1, len(campaign.recipients), campaign)

            except FloodWaitError as e:
                logger.warning(f"FloodWait: {e.seconds}s")
                await self._notify("flood_wait", seconds=e.seconds, campaign=campaign)
                await asyncio.sleep(e.seconds)
                # Retry this recipient
                continue

            except Exception as e:
                recipient.status = "error"
                recipient.error_message = str(e)
                logger.error(f"Error sending to {phone}: {e}")

            # Антибан задержка
            delay = random.uniform(settings.outreach_delay_min, settings.outreach_delay_max)
            await asyncio.sleep(delay)

        # Фаза 1 завершена — переход к слушанию ответов
        logger.info(f"Sending loop finished. cancelled={self._cancelled}, sent={campaign.sent_count}")
        if not self._cancelled:
            campaign.status = "listening"
            await self._notify("sending_complete", campaign=campaign)
            logger.info("Campaign status: listening")

    # ─── Фаза 2a: Слушатель входящих ответов ───

    def _find_recipient(self, sender_id: int) -> Optional[OutreachRecipient]:
        """Динамически ищет получателя по telegram_user_id."""
        if not self._campaign:
            return None
        for r in self._campaign.recipients:
            if r.telegram_user_id == sender_id:
                return r
        return None

    async def start_listener(self) -> None:
        """Запускает event handler для входящих сообщений."""
        if not self._campaign:
            return

        client_wrapper = await get_sherlock_client()
        client = client_wrapper.client

        # Логируем target IDs для отладки
        target_ids = [
            r.telegram_user_id
            for r in self._campaign.recipients
            if r.telegram_user_id
        ]
        logger.info(f"Listener target IDs: {target_ids}")

        # НЕ используем from_users фильтр — он замораживается при регистрации
        # и может не совпадать. Фильтруем вручную через _find_recipient.
        @client.on(events.NewMessage(incoming=True))
        async def on_incoming(event):
            if self._cancelled:
                return

            sender_id = event.sender_id

            # Динамический поиск
            recipient = self._find_recipient(sender_id)
            if not recipient:
                # Не наш получатель — игнорируем молча
                return

            if recipient.status in ("warm", "rejected", "no_response"):
                return  # Диалог завершён

            logger.info(f"Incoming from {sender_id} ({recipient.company_name}): {event.text[:80]}")

            # Добавляем сообщение в историю
            recipient.conversation_history.append({
                "role": "user",
                "content": event.text,
            })
            recipient.last_message_at = datetime.now(timezone.utc)
            recipient.ping_count = 0
            recipient.status = "talking"

            # Отмечаем сообщение как прочитанное
            try:
                await event.mark_read()
            except Exception:
                pass

            # Генерируем AI ответ
            try:
                ai_response = await self.ai_engine.generate_response(
                    recipient.conversation_history,
                    self._campaign.system_prompt or None,
                )
            except Exception as e:
                logger.error(f"AI error for {sender_id}: {e}")
                return

            if not ai_response:
                logger.error(f"AI returned None for {sender_id}")
                return

            reply_text = ai_response["reply"]
            status = ai_response.get("status", "talking")

            logger.info(f"AI reply to {sender_id}: status={status}, text={reply_text[:80]}")

            # Задержка перед ответом с индикатором "печатает"
            delay = random.uniform(
                settings.outreach_reply_delay_min,
                settings.outreach_reply_delay_max,
            )
            async with client.action(sender_id, 'typing'):
                await asyncio.sleep(delay)

            # Отправляем ответ
            try:
                await client.send_message(sender_id, reply_text)

                recipient.conversation_history.append({
                    "role": "assistant",
                    "content": reply_text,
                })
                recipient.last_message_at = datetime.now(timezone.utc)

                if status == "warm":
                    recipient.status = "warm"
                    self._campaign.warm_count += 1
                    await self._notify("warm_lead", recipient=recipient, campaign=self._campaign)

                elif status == "rejected":
                    recipient.status = "rejected"
                    self._campaign.rejected_count += 1

                logger.info(f"Sent reply to {recipient.company_name}, status={recipient.status}")

            except FloodWaitError as e:
                logger.warning(f"FloodWait on reply: {e.seconds}s")
                await asyncio.sleep(e.seconds)

            except Exception as e:
                logger.error(f"Error replying to {sender_id}: {e}")

        self._listener_handler = on_incoming
        logger.info(f"Listener started, tracking {len(target_ids)} recipients")

    # ─── Фаза 2b: Автопинг при игноре ───

    async def _ping_loop(self) -> None:
        """Фоновый цикл автопинга каждые 30 минут."""
        while not self._cancelled and self._campaign:
            await asyncio.sleep(30 * 60)  # 30 минут

            if self._cancelled:
                break

            await self._pause_event.wait()

            if not self._is_working_hours():
                continue

            client_wrapper = await get_sherlock_client()
            client = client_wrapper.client
            now = datetime.now(timezone.utc)

            for recipient in self._campaign.recipients:
                if self._cancelled:
                    break

                if recipient.status not in ("sent", "talking"):
                    continue

                if not recipient.last_message_at:
                    continue

                hours_since = (now - recipient.last_message_at).total_seconds() / 3600

                if hours_since < settings.outreach_ping_interval_hours:
                    continue

                if recipient.ping_count >= settings.outreach_max_pings:
                    recipient.status = "no_response"
                    continue

                # Генерируем follow-up
                followup = await self.ai_engine.generate_followup(
                    recipient.conversation_history
                )

                if not followup:
                    continue

                try:
                    await client.send_message(recipient.telegram_user_id, followup)

                    recipient.conversation_history.append({
                        "role": "assistant",
                        "content": followup,
                    })
                    recipient.last_message_at = datetime.now(timezone.utc)
                    recipient.ping_count += 1

                    logger.info(
                        f"Ping #{recipient.ping_count} to {recipient.company_name}"
                    )

                    # Задержка между пингами
                    await asyncio.sleep(random.uniform(10, 30))

                except FloodWaitError as e:
                    logger.warning(f"FloodWait on ping: {e.seconds}s")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    logger.error(f"Ping error for {recipient.company_name}: {e}")

    def _is_working_hours(self) -> bool:
        """Проверяет рабочее время (9:00-21:00 МСК)."""
        now_msk = datetime.now(timezone.utc) + MSK_OFFSET
        return settings.outreach_work_hour_start <= now_msk.hour < settings.outreach_work_hour_end

    # ─── Управление кампанией ───

    def pause(self) -> None:
        """Приостанавливает кампанию."""
        self._pause_event.clear()
        if self._campaign:
            self._campaign.status = "paused"

    def resume(self) -> None:
        """Возобновляет кампанию."""
        self._pause_event.set()
        if self._campaign:
            self._campaign.status = "listening" if self._campaign.sent_count > 0 else "sending"

    async def cancel(self) -> None:
        """Отменяет кампанию."""
        self._cancelled = True
        self._pause_event.set()  # Разблокировать если на паузе

        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()

        # Удаляем event handler
        if self._listener_handler:
            try:
                client_wrapper = await get_sherlock_client()
                client_wrapper.client.remove_event_handler(self._listener_handler)
            except Exception:
                pass

        # Удаляем контакты
        await self._cleanup_contacts()

        if self._campaign:
            self._campaign.status = "cancelled"

    async def _cleanup_contacts(self) -> None:
        """Удаляет добавленные контакты."""
        if not self._campaign:
            return

        try:
            client_wrapper = await get_sherlock_client()
            client = client_wrapper.client

            user_ids = [
                r.telegram_user_id
                for r in self._campaign.recipients
                if r.telegram_user_id
            ]

            if user_ids:
                # Получаем entities для удаления
                for uid in user_ids:
                    try:
                        entity = await client.get_input_entity(uid)
                        await client(DeleteContactsRequest([entity]))
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Cleanup contacts error: {e}")

    @property
    def campaign(self) -> Optional[OutreachCampaign]:
        return self._campaign


# Глобальные активные кампании: user_id -> OutreachService
active_outreach: dict[int, OutreachService] = {}
