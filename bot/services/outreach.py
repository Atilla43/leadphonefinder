"""Ядро AI-продажника: рассылка + слушатель ответов + автопинг."""

import asyncio
import logging
import random
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Awaitable

from telethon import events
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputPhoneContact, InputStickerSetShortName
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


def extract_first_name(full_name: str) -> str:
    """Извлекает имя (не фамилию) из ФИО. 'Шевченко Дмитрий' → 'Дмитрий'."""
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return parts[1]  # Фамилия Имя → берём имя
    return parts[0] if parts else ""


def render_first_message(offer: str, recipient: OutreachRecipient) -> str:
    """Формирует первое сообщение для лида."""
    name = extract_first_name(recipient.contact_name) if recipient.contact_name else ""
    company = recipient.company_name
    greeting = f"{name}, здравствуйте" if name else "Здравствуйте"
    return f"{greeting}, я очень коротко по поводу {company}.\n\n{offer}"


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

            # Ждём рабочие часы (10-17 МСК)
            await self._wait_for_working_hours()
            if self._cancelled:
                break

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
            logger.info(f"[LISTENER] New incoming message from {event.sender_id}: {(event.text or '')[:80]}")

            if self._cancelled:
                logger.info("[LISTENER] Cancelled, skipping")
                return

            sender_id = event.sender_id

            # Динамический поиск
            recipient = self._find_recipient(sender_id)
            if not recipient:
                # Не наш получатель — игнорируем молча
                logger.debug(f"[LISTENER] sender {sender_id} not in recipients, ignoring")
                return

            if recipient.status in ("warm", "rejected", "no_response"):
                logger.info(f"[LISTENER] Recipient {recipient.company_name} status={recipient.status}, skipping")
                return  # Диалог завершён

            logger.info(f"[LISTENER] Processing message from {sender_id} ({recipient.company_name}): {event.text[:80]}")

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

            # Генерируем AI ответ (с retry при пустом ответе)
            ai_response = None
            for attempt in range(3):
                logger.info(f"[LISTENER] Calling AI for {sender_id}, attempt={attempt+1}, history len={len(recipient.conversation_history)}")
                try:
                    ai_response = await self.ai_engine.generate_response(
                        recipient.conversation_history,
                        self._campaign.system_prompt or None,
                        company_context=self._build_company_context(recipient),
                    )
                except Exception as e:
                    logger.error(f"[LISTENER] AI error for {sender_id}: {e}", exc_info=True)

                if ai_response:
                    break
                logger.warning(f"[LISTENER] AI returned None for {sender_id}, attempt {attempt+1}/3")
                await asyncio.sleep(2)

            if not ai_response:
                logger.error(f"[LISTENER] AI failed after 3 attempts for {sender_id}")
                return

            reply_text = ai_response["reply"]
            status = ai_response.get("status", "talking")

            logger.info(f"AI reply to {sender_id}: status={status}, text={reply_text[:80]}")

            # Задержка перед ответом с индикатором "печатает"
            # Базовая задержка + ~0.05-0.08 сек на символ (имитация печати)
            char_delay = len(reply_text) * random.uniform(0.05, 0.08)
            base_delay = random.uniform(2.0, 4.0)
            delay = min(base_delay + char_delay, 45.0)
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

    # ─── Фаза 2b: Follow-up при игноре ───

    async def _send_cat_sticker(self, client, user_id: int) -> None:
        """Отправляет случайный стикер с котиком."""
        try:
            sticker_set = await client(GetStickerSetRequest(
                stickerset=InputStickerSetShortName(
                    short_name=settings.outreach_sticker_pack
                ),
                hash=0
            ))
            if sticker_set.documents:
                sticker = random.choice(sticker_set.documents)
                await client.send_file(user_id, sticker)
                logger.info(f"Sent cat sticker to {user_id}")
        except Exception as e:
            logger.error(f"Failed to send sticker: {e}")

    async def _ping_loop(self) -> None:
        """Фоновый цикл follow-up: день 2 — сообщение, день 3 — стикер."""
        while not self._cancelled and self._campaign:
            await asyncio.sleep(60 * 60)  # Проверяем каждый час

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

                days_since = (now - recipient.last_message_at).total_seconds() / 86400

                if days_since < 1:
                    continue

                try:
                    if recipient.ping_count == 0:
                        # День 2: персонализированное сообщение
                        name = extract_first_name(recipient.contact_name) if recipient.contact_name else ""
                        if name:
                            text = f"{name}, подниму сообщение)) возможно, потерялось 🌷"
                        else:
                            text = "Подниму сообщение)) возможно, потерялось 🌷"

                        await client.send_message(recipient.telegram_user_id, text)
                        recipient.conversation_history.append({
                            "role": "assistant",
                            "content": text,
                        })
                        recipient.last_message_at = now
                        recipient.ping_count = 1
                        logger.info(f"Follow-up day 2 to {recipient.company_name}")

                    elif recipient.ping_count == 1:
                        # День 3: стикер с котиком
                        await self._send_cat_sticker(client, recipient.telegram_user_id)
                        recipient.last_message_at = now
                        recipient.ping_count = 2
                        logger.info(f"Follow-up day 3 (sticker) to {recipient.company_name}")

                    elif recipient.ping_count >= 2:
                        recipient.status = "no_response"
                        continue

                    await asyncio.sleep(random.uniform(10, 30))

                except FloodWaitError as e:
                    logger.warning(f"FloodWait on ping: {e.seconds}s")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    logger.error(f"Ping error for {recipient.company_name}: {e}")

    @staticmethod
    def _build_company_context(recipient: OutreachRecipient) -> Optional[str]:
        """Формирует контекст о компании для AI."""
        parts = []
        if recipient.category:
            parts.append(f"Категория: {recipient.category}")
        if recipient.rating:
            rating_str = f"Рейтинг: {recipient.rating}"
            if recipient.reviews_count:
                rating_str += f" ({recipient.reviews_count} отзывов)"
            parts.append(rating_str)
        if recipient.website:
            parts.append(f"Сайт: {recipient.website}")
        if recipient.working_hours:
            parts.append(f"Время работы: {recipient.working_hours}")
        if recipient.address:
            parts.append(f"Адрес: {recipient.address}")
        if recipient.director_name:
            parts.append(f"Директор: {recipient.director_name}")
        return "\n".join(parts) if parts else None

    def _is_working_hours(self) -> bool:
        """Проверяет рабочее время (10:00-17:00 МСК)."""
        now_msk = datetime.now(timezone.utc) + MSK_OFFSET
        return settings.outreach_work_hour_start <= now_msk.hour < settings.outreach_work_hour_end

    async def _wait_for_working_hours(self) -> None:
        """Ждёт наступления рабочих часов (МСК). Если сейчас вне часов — спит до начала."""
        while not self._is_working_hours():
            if self._cancelled:
                return
            now_msk = datetime.now(timezone.utc) + MSK_OFFSET
            if now_msk.hour >= settings.outreach_work_hour_end:
                # Уже вечер — ждём до завтра
                tomorrow = now_msk + timedelta(days=1)
                target = tomorrow.replace(
                    hour=settings.outreach_work_hour_start, minute=0, second=0, microsecond=0
                )
            else:
                # Утро до начала рабочего дня
                target = now_msk.replace(
                    hour=settings.outreach_work_hour_start, minute=0, second=0, microsecond=0
                )
            sleep_seconds = (target - now_msk).total_seconds()
            logger.info(f"Outside working hours ({now_msk.strftime('%H:%M')} MSK). Sleeping {sleep_seconds/3600:.1f}h until {settings.outreach_work_hour_start}:00")
            await self._notify("waiting_hours", campaign=self._campaign, sleep_hours=sleep_seconds / 3600)
            # Спим порциями по 5 минут чтобы можно было отменить
            while sleep_seconds > 0 and not self._cancelled:
                chunk = min(sleep_seconds, 300)
                await asyncio.sleep(chunk)
                sleep_seconds -= chunk

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
