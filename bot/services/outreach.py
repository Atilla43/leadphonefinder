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
from bot.services.account_pool import get_account_pool, AccountPool
from bot.services.outreach_storage import OutreachStorage
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
    """Извлекает имя из ФИО. Поддерживает форматы:
    - 'Фамилия Имя Отчество' → Имя
    - 'Имя Отчество' → Имя
    - 'Имя' → Имя
    """
    parts = full_name.strip().split()
    if not parts:
        return ""

    def is_patronymic(word: str) -> bool:
        w = word.lower()
        return w.endswith(("ович", "евич", "ич", "овна", "евна", "ична"))

    if len(parts) == 1:
        name = parts[0]
    elif len(parts) == 2:
        if is_patronymic(parts[1]):
            name = parts[0]  # Микаел Седракович → Микаел
        else:
            name = parts[1]  # Шевченко Дмитрий → Дмитрий
    else:
        name = parts[1]  # Иванов Пётр Сергеевич → Пётр

    return name.capitalize()


def detect_gender(full_name: str) -> str:
    """Определяет пол по отчеству: male/female/unknown."""
    for part in full_name.strip().split():
        w = part.lower()
        if w.endswith(("овна", "евна", "ична")):
            return "female"
        if w.endswith(("ович", "евич")):
            return "male"
    return "unknown"


def render_first_message(offer: str, recipient: OutreachRecipient) -> str:
    """Формирует первое сообщение для лида."""
    name = extract_first_name(recipient.contact_name) if recipient.contact_name else ""
    company = recipient.company_name
    greeting = f"{name}, здравствуйте" if name else "Здравствуйте"
    return f"{greeting}, коротко по «{company}».\n\n{offer}"


class OutreachService:
    """Сервис AI-продажника."""

    def __init__(self, ai_engine: AISalesEngine):
        self.ai_engine = ai_engine
        self._storage = OutreachStorage()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        self._cancelled = False
        self._campaign: Optional[OutreachCampaign] = None
        self._listener_handler = None
        self._listener_handlers: list = []
        self._ping_task: Optional[asyncio.Task] = None
        self._notify_callback: Optional[Callable] = None
        # Дебаунс: собираем сообщения перед обработкой
        self._pending_messages: dict[int, list[str]] = {}  # sender_id → [texts]
        self._debounce_tasks: dict[int, asyncio.Task] = {}  # sender_id → task
        self._process_locks: dict[int, asyncio.Lock] = {}  # sender_id → lock
        self.next_send_at: Optional[datetime] = None  # время следующей отправки (UTC)

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

    def _save(self) -> None:
        """Сохраняет текущее состояние кампании на диск."""
        if self._campaign:
            try:
                self._storage.save(self._campaign)
            except Exception as e:
                logger.error(f"Failed to save campaign: {e}")

    # ─── Фаза 1: Рассылка первых сообщений ───

    def _calc_send_interval(self) -> float:
        """Рассчитывает интервал между отправками чтобы растянуть на рабочий день."""
        now_msk = datetime.now(timezone.utc) + MSK_OFFSET
        end_hour = settings.outreach_work_hour_end
        remaining_hours = max(end_hour - now_msk.hour - now_msk.minute / 60, 0.5)
        remaining_seconds = remaining_hours * 3600

        pool = get_account_pool()
        # Сколько ещё можно отправить сегодня со всех аккаунтов
        remaining_capacity = 0
        for a in pool.get_active_accounts():
            remaining_capacity += settings.outreach_daily_limit - pool.sent_today.get(a.phone, 0)
        remaining_capacity = max(remaining_capacity, 1)

        # Сколько pending получателей осталось
        pending = sum(1 for r in self._campaign.recipients if r.status == "pending") if self._campaign else 1
        sends_planned = min(pending, remaining_capacity)
        sends_planned = max(sends_planned, 1)

        interval = remaining_seconds / sends_planned
        return max(interval, 30)  # Минимум 30 сек

    async def start_campaign(
        self,
        campaign: OutreachCampaign,
        progress_callback: Optional[Callable[..., Awaitable]] = None,
        resume: bool = False,
    ) -> None:
        """Запускает фазу 1: рассылка первых сообщений."""
        pool = get_account_pool()
        if not pool.get_active_accounts():
            raise RuntimeError("Нет подключённых аккаунтов. Добавьте номер через меню.")

        self._campaign = campaign
        self._cancelled = False
        self._pause_event.set()
        campaign.status = "sending"

        if not resume:
            # Распределяем получателей по аккаунтам (round-robin)
            pool.assign_recipients(campaign.recipients, settings.outreach_daily_limit)
            self._save()

            # Запускаем listener СРАЗУ, до рассылки — чтобы ловить быстрые ответы
            await self.start_listener()
            self._ping_task = asyncio.create_task(self._ping_loop())

        total_sent = 0

        for i, recipient in enumerate(campaign.recipients):
            if self._cancelled:
                break

            if recipient.status != "pending":
                continue

            # Проверка паузы
            await self._pause_event.wait()

            # Ждём рабочие часы (10-17 МСК)
            await self._wait_for_working_hours()
            if self._cancelled:
                break

            # Проверяем лимиты всех аккаунтов
            if pool.all_limits_reached(settings.outreach_daily_limit):
                logger.info("All accounts reached daily limit, waiting for next work day")
                await self._notify("daily_limit", campaign=campaign)
                # Ждём до 10:00 следующего рабочего дня
                await self._wait_until_next_work_day()
                if self._cancelled:
                    break
                pool.reset_daily_counters()

            # Берём клиент для этого получателя
            account_phone = recipient.account_phone
            client = pool.get_client(account_phone) if account_phone else None

            if not client:
                # Fallback: берём любой доступный
                result = pool.get_next_available(settings.outreach_daily_limit)
                if not result:
                    logger.warning("No available accounts, waiting...")
                    await self._wait_for_working_hours()
                    pool.reset_daily_counters()
                    continue
                client, account_info = result
                recipient.account_phone = account_info.phone

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
                total_sent += 1
                pool.increment_sent(recipient.account_phone)

                logger.info(f"Sent to {phone} ({recipient.company_name}) from {recipient.account_phone}")
                self._save()

                # Прогресс
                if progress_callback:
                    await progress_callback(i + 1, len(campaign.recipients), campaign)

            except FloodWaitError as e:
                logger.warning(f"FloodWait: {e.seconds}s")
                await self._notify("flood_wait", seconds=e.seconds, campaign=campaign)
                await asyncio.sleep(e.seconds)
                continue

            except Exception as e:
                recipient.status = "error"
                recipient.error_message = str(e)
                logger.error(f"Error sending to {phone}: {e}")

            # Растянутая задержка (≈14 мин при 30/день на 7 часов)
            interval = self._calc_send_interval()
            jitter = random.uniform(-120, 120)  # ±2 мин
            delay = max(interval + jitter, 15)
            self.next_send_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            logger.debug(f"Next send in {delay:.0f}s (interval={interval:.0f}s)")
            await asyncio.sleep(delay)

        # Фаза 1 завершена — переход к слушанию ответов
        self.next_send_at = None
        logger.info(f"Sending loop finished. cancelled={self._cancelled}, sent={campaign.sent_count}")
        if not self._cancelled:
            campaign.status = "listening"
            self._save()
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

    def _get_client_for_recipient(self, recipient: OutreachRecipient) -> Optional["TelegramClient"]:
        """Получает Telethon клиент для конкретного получателя."""
        pool = get_account_pool()
        if recipient.account_phone:
            client = pool.get_client(recipient.account_phone)
            if client:
                return client
        # Fallback: первый доступный клиент
        clients = pool.get_all_clients()
        return clients[0] if clients else None

    async def start_listener(self) -> None:
        """Запускает event handler для входящих сообщений на ВСЕХ клиентах."""
        if not self._campaign:
            return

        pool = get_account_pool()
        all_clients = pool.get_all_clients()

        if not all_clients:
            # Fallback на старый singleton
            try:
                client_wrapper = await get_sherlock_client()
                all_clients = [client_wrapper.client]
            except Exception:
                logger.error("No clients available for listener")
                return

        # Логируем target IDs для отладки
        target_ids = [
            r.telegram_user_id
            for r in self._campaign.recipients
            if r.telegram_user_id
        ]
        logger.info(f"Listener target IDs: {target_ids}")

        self._listener_handlers = []

        for client in all_clients:
            # НЕ используем from_users фильтр — он замораживается при регистрации
            @client.on(events.NewMessage(incoming=True))
            async def on_incoming(event, _client=client):
                if self._cancelled:
                    return

                sender_id = event.sender_id

                # Динамический поиск
                recipient = self._find_recipient(sender_id)
                if not recipient:
                    return

                # Извлекаем текст + контакт-карточку
                text = event.text or ""
                if event.message.contact:
                    c = event.message.contact
                    contact_phone = c.phone_number or ""
                    contact_name = f"{c.first_name or ''} {c.last_name or ''}".strip()
                    text += f"\n[Контакт: {contact_name}, {contact_phone}]"

                if not text.strip():
                    return

                logger.info(f"[LISTENER] New message from {sender_id}: {text[:80]}")

                try:
                    await event.mark_read()
                except Exception:
                    pass

                # Статусы которые не нуждаются в дебаунсе
                if recipient.status in ("rejected", "no_response"):
                    logger.info(f"[LISTENER] Recipient {recipient.company_name} status={recipient.status}, skipping")
                    return

                if recipient.status == "warm_confirmed":
                    recipient.conversation_history.append({"role": "user", "content": text})
                    recipient.last_message_at = datetime.now(timezone.utc)
                    self._save()
                    await self._notify("warm_lead_reply", recipient=recipient, campaign=self._campaign)
                    logger.info(f"[LISTENER] Confirmed lead {recipient.company_name} replied: {text[:80]}")
                    return

                # Дебаунс: собираем сообщения 3 секунды перед обработкой
                if sender_id not in self._pending_messages:
                    self._pending_messages[sender_id] = []
                self._pending_messages[sender_id].append(text)

                # Отменяем предыдущий debounce task
                if sender_id in self._debounce_tasks:
                    self._debounce_tasks[sender_id].cancel()

                self._debounce_tasks[sender_id] = asyncio.create_task(
                    self._debounced_process(sender_id, _client)
                )

            self._listener_handlers.append(on_incoming)

        self._listener_handler = self._listener_handlers[0] if self._listener_handlers else None
        logger.info(f"Listener started on {len(all_clients)} client(s), tracking {len(target_ids)} recipients")

    async def _debounced_process(self, sender_id: int, fallback_client) -> None:
        """Ждёт 3 сек, собирает все сообщения от sender_id, обрабатывает как одно."""
        await asyncio.sleep(3)

        messages = self._pending_messages.pop(sender_id, [])
        self._debounce_tasks.pop(sender_id, None)

        if not messages or self._cancelled:
            return

        # Лок: ждём пока предыдущая обработка для этого sender завершится
        if sender_id not in self._process_locks:
            self._process_locks[sender_id] = asyncio.Lock()

        async with self._process_locks[sender_id]:
            # После получения лока проверяем — не пришли ли ещё сообщения пока ждали
            extra = self._pending_messages.pop(sender_id, [])
            if extra:
                messages.extend(extra)
                # Отменяем дебаунс-таск для этих сообщений, мы их уже забрали
                task = self._debounce_tasks.pop(sender_id, None)
                if task:
                    task.cancel()
            await self._process_recipient_messages(sender_id, messages, fallback_client)

    async def _process_recipient_messages(self, sender_id: int, messages: list[str], fallback_client) -> None:
        """Обрабатывает собранные сообщения от получателя (под локом)."""
        combined_text = "\n".join(messages)

        recipient = self._find_recipient(sender_id)
        if not recipient:
            return

        reply_client = self._get_client_for_recipient(recipient) or fallback_client

        # Warm-лид: AI отправляет финальное подтверждение
        if recipient.status == "warm":
            recipient.conversation_history.append({"role": "user", "content": combined_text})
            recipient.last_message_at = datetime.now(timezone.utc)

            ai_response = None
            try:
                ai_response = await self.ai_engine.generate_response(
                    recipient.conversation_history,
                    self._campaign.system_prompt or None,
                    company_context=self._build_company_context(recipient),
                )
            except Exception as e:
                logger.error(f"[LISTENER] AI error for warm confirm: {e}")

            if ai_response:
                reply_text = ai_response["reply"]
                await self._send_with_typing(reply_client, sender_id, reply_text)
                recipient.conversation_history.append({"role": "assistant", "content": reply_text})

            recipient.status = "warm_confirmed"
            self._save()
            await self._notify("warm_lead_reply", recipient=recipient, campaign=self._campaign)
            logger.info(f"[LISTENER] Warm lead {recipient.company_name} confirmed")
            return

        # Обычная обработка
        logger.info(f"[LISTENER] Processing {len(messages)} message(s) from {sender_id} ({recipient.company_name})")

        recipient.conversation_history.append({"role": "user", "content": combined_text})
        recipient.last_message_at = datetime.now(timezone.utc)
        recipient.ping_count = 0
        recipient.status = "talking"

        # Генерируем AI ответ (с retry)
        ai_response = None
        for attempt in range(3):
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
            logger.warning(f"[LISTENER] AI returned None, attempt {attempt+1}/3")
            await asyncio.sleep(2)

        if not ai_response:
            logger.error(f"[LISTENER] AI failed after 3 attempts for {sender_id}")
            return

        reply_text = ai_response["reply"]
        status = ai_response.get("status", "talking")
        logger.info(f"AI reply to {sender_id}: status={status}, text={reply_text[:80]}")

        try:
            await self._send_with_typing(reply_client, sender_id, reply_text)

            recipient.conversation_history.append({"role": "assistant", "content": reply_text})
            recipient.last_message_at = datetime.now(timezone.utc)

            if status == "warm":
                recipient.status = "warm"
                self._campaign.warm_count += 1
                await self._notify("warm_lead", recipient=recipient, campaign=self._campaign)
            elif status == "rejected":
                recipient.status = "rejected"
                self._campaign.rejected_count += 1
            elif status == "referral":
                recipient.status = "referral"
                await self._handle_referral(recipient, combined_text, reply_client)

            logger.info(f"Sent reply to {recipient.company_name}, status={recipient.status}")
            self._save()

        except FloodWaitError as e:
            logger.warning(f"FloodWait on reply: {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Error replying to {sender_id}: {e}")

    async def _send_with_typing(self, client, user_id: int, text: str) -> None:
        """Отправляет сообщение с имитацией набора текста."""
        char_delay = len(text) * random.uniform(0.05, 0.08)
        base_delay = random.uniform(2.0, 4.0)
        delay = min(base_delay + char_delay, 45.0)
        async with client.action(user_id, 'typing'):
            await asyncio.sleep(delay)
        await client.send_message(user_id, text)

    async def _handle_referral(self, original_recipient: OutreachRecipient, text: str, client) -> None:
        """Обработка перенаправления: извлекает контакт и пишет новому получателю."""
        # Извлекаем телефон и имя из [Контакт: имя, +7...]
        match = re.search(r'\[Контакт:\s*(.+?),\s*(\+?\d[\d\s-]+)\]', text)
        if not match:
            logger.info(f"[REFERRAL] No contact found in message from {original_recipient.company_name}")
            await self._notify("referral", recipient=original_recipient, campaign=self._campaign,
                               referral_name=None, referral_phone=None)
            return

        referral_name = match.group(1).strip()
        referral_phone = normalize_phone(match.group(2).strip())

        logger.info(f"[REFERRAL] {original_recipient.company_name} -> {referral_name} ({referral_phone})")

        # Проверяем что такого телефона ещё нет в кампании
        for r in self._campaign.recipients:
            if normalize_phone(r.phone) == referral_phone:
                logger.info(f"[REFERRAL] Phone {referral_phone} already in campaign, skipping")
                await self._notify("referral", recipient=original_recipient, campaign=self._campaign,
                                   referral_name=referral_name, referral_phone=referral_phone)
                return

        # Формируем выжимку из оригинальной переписки
        referral_summary = f"Перенаправлен от: {original_recipient.company_name}"
        if original_recipient.contact_name:
            referral_summary += f" ({original_recipient.contact_name})"
        referral_summary += "\nИстория переписки с ним:\n"
        for msg in original_recipient.conversation_history:
            role = "Мы" if msg["role"] == "assistant" else "Клиент"
            referral_summary += f"- {role}: {msg['content'][:150]}\n"

        # Создаём нового получателя
        new_recipient = OutreachRecipient(
            phone=referral_phone,
            company_name=original_recipient.company_name,
            contact_name=referral_name,
            category=original_recipient.category,
            address=original_recipient.address,
            account_phone=original_recipient.account_phone,
            referral_context=referral_summary,
        )

        # Импортируем контакт через Telethon
        try:
            contact = InputPhoneContact(
                client_id=0,
                phone=referral_phone,
                first_name=referral_name,
                last_name="",
            )
            result = await client(ImportContactsRequest([contact]))

            if not result.users:
                logger.info(f"[REFERRAL] Phone {referral_phone} not in Telegram")
                new_recipient.status = "not_found"
                self._campaign.recipients.append(new_recipient)
                await self._notify("referral", recipient=original_recipient, campaign=self._campaign,
                                   referral_name=referral_name, referral_phone=referral_phone,
                                   referral_found=False)
                return

            user = result.users[0]
            new_recipient.telegram_user_id = user.id

            # Отправляем первое сообщение с упоминанием перенаправления
            first_name = extract_first_name(referral_name) if referral_name else ""
            greeting = f"{first_name}, здравствуйте" if first_name else "Здравствуйте"
            referral_msg = (
                f"{greeting}! {original_recipient.company_name} порекомендовала "
                f"обратиться к вам.\n\n{self._campaign.offer}"
            )

            await self._send_with_typing(client, user.id, referral_msg)

            new_recipient.status = "sent"
            new_recipient.last_message_at = datetime.now(timezone.utc)
            new_recipient.conversation_history.append({
                "role": "assistant",
                "content": referral_msg,
            })
            self._campaign.recipients.append(new_recipient)
            self._campaign.sent_count += 1
            self._save()

            logger.info(f"[REFERRAL] Sent first message to {referral_name} ({referral_phone})")
            await self._notify("referral", recipient=original_recipient, campaign=self._campaign,
                               referral_name=referral_name, referral_phone=referral_phone,
                               referral_found=True)

        except FloodWaitError as e:
            logger.warning(f"[REFERRAL] FloodWait: {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"[REFERRAL] Error sending to {referral_phone}: {e}")

    # ─── Фаза 2b: Follow-up при игноре ───

    async def _send_cat_sticker(self, client, user_id: int) -> None:
        """Отправляет конкретный стикер из пака."""
        try:
            sticker_set = await client(GetStickerSetRequest(
                stickerset=InputStickerSetShortName(
                    short_name=settings.outreach_sticker_pack
                ),
                hash=0
            ))
            if sticker_set.documents:
                idx = settings.outreach_sticker_index
                if idx < len(sticker_set.documents):
                    sticker = sticker_set.documents[idx]
                else:
                    sticker = sticker_set.documents[0]
                    logger.warning(f"Sticker index {idx} out of range ({len(sticker_set.documents)}), using first")
                await client.send_file(user_id, sticker)
                logger.info(f"Sent sticker #{idx + 1} to {user_id}")
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

            now = datetime.now(timezone.utc)

            for recipient in self._campaign.recipients:
                if self._cancelled:
                    break

                if recipient.status not in ("sent", "talking"):
                    continue

                if not recipient.telegram_user_id:
                    continue

                if not recipient.last_message_at:
                    continue

                days_since = (now - recipient.last_message_at).total_seconds() / 86400

                if days_since < 1:
                    continue

                # Используем клиент с которого было отправлено
                client = self._get_client_for_recipient(recipient)
                if not client:
                    try:
                        client_wrapper = await get_sherlock_client()
                        client = client_wrapper.client
                    except Exception:
                        logger.error(f"No client for ping to {recipient.company_name}")
                        continue

                try:
                    if recipient.ping_count == 0:
                        name = extract_first_name(recipient.contact_name) if recipient.contact_name else ""
                        gender = detect_gender(recipient.contact_name) if recipient.contact_name else "unknown"
                        if name:
                            if gender == "female":
                                text = f"{name}, подниму сообщение)) возможно, потерялось 🌷"
                            else:
                                text = f"{name}, подниму сообщение)) возможно, потерялось"
                        else:
                            text = "Подниму сообщение)) возможно, потерялось"

                        await client.send_message(recipient.telegram_user_id, text)
                        recipient.conversation_history.append({
                            "role": "assistant",
                            "content": text,
                        })
                        recipient.last_message_at = now
                        recipient.ping_count = 1
                        logger.info(f"Follow-up day 2 to {recipient.company_name}")
                        self._save()

                    elif recipient.ping_count == 1:
                        await self._send_cat_sticker(client, recipient.telegram_user_id)
                        recipient.last_message_at = now
                        recipient.ping_count = 2
                        logger.info(f"Follow-up day 3 (sticker) to {recipient.company_name}")
                        self._save()

                    elif recipient.ping_count >= 2:
                        recipient.status = "no_response"
                        self._save()
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
        if recipient.referral_context:
            parts.append(f"\n{recipient.referral_context}")
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
            self.next_send_at = datetime.now(timezone.utc) + timedelta(seconds=sleep_seconds)
            logger.info(f"Outside working hours ({now_msk.strftime('%H:%M')} MSK). Sleeping {sleep_seconds/3600:.1f}h until {settings.outreach_work_hour_start}:00")
            await self._notify("waiting_hours", campaign=self._campaign, sleep_hours=sleep_seconds / 3600)
            # Спим порциями по 5 минут чтобы можно было отменить
            while sleep_seconds > 0 and not self._cancelled:
                chunk = min(sleep_seconds, 300)
                await asyncio.sleep(chunk)
                sleep_seconds -= chunk

    async def _wait_until_next_work_day(self) -> None:
        """Ждёт до 10:00 МСК следующего дня (при достижении дневного лимита)."""
        now_msk = datetime.now(timezone.utc) + MSK_OFFSET
        tomorrow = now_msk + timedelta(days=1)
        target = tomorrow.replace(
            hour=settings.outreach_work_hour_start, minute=0, second=0, microsecond=0
        )
        sleep_seconds = (target - now_msk).total_seconds()
        self.next_send_at = datetime.now(timezone.utc) + timedelta(seconds=sleep_seconds)
        logger.info(f"Daily limit reached. Sleeping {sleep_seconds/3600:.1f}h until tomorrow {settings.outreach_work_hour_start}:00 MSK")
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
            self._save()

    def resume(self) -> None:
        """Возобновляет кампанию."""
        self._pause_event.set()
        if self._campaign:
            self._campaign.status = "listening" if self._campaign.sent_count > 0 else "sending"
            self._save()

    async def cancel(self) -> None:
        """Отменяет кампанию."""
        self._cancelled = True
        self._pause_event.set()  # Разблокировать если на паузе

        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()

        # Удаляем event handlers со всех клиентов
        pool = get_account_pool()
        for handler in getattr(self, '_listener_handlers', []):
            for client in pool.get_all_clients():
                try:
                    client.remove_event_handler(handler)
                except Exception:
                    pass

        # Fallback: старый singleton
        if self._listener_handler and not getattr(self, '_listener_handlers', []):
            try:
                client_wrapper = await get_sherlock_client()
                client_wrapper.client.remove_event_handler(self._listener_handler)
            except Exception:
                pass

        # Удаляем контакты
        await self._cleanup_contacts()

        if self._campaign:
            self._campaign.status = "cancelled"
            self._storage.delete(self._campaign.user_id, self._campaign.campaign_id)

    async def _cleanup_contacts(self) -> None:
        """Удаляет добавленные контакты."""
        if not self._campaign:
            return

        try:
            pool = get_account_pool()

            for recipient in self._campaign.recipients:
                if not recipient.telegram_user_id:
                    continue
                client = self._get_client_for_recipient(recipient)
                if not client:
                    continue
                try:
                    entity = await client.get_input_entity(recipient.telegram_user_id)
                    await client(DeleteContactsRequest([entity]))
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Cleanup contacts error: {e}")

    @property
    def campaign(self) -> Optional[OutreachCampaign]:
        return self._campaign


# Глобальные активные кампании: user_id -> {campaign_id -> OutreachService}
active_outreach: dict[int, dict[str, OutreachService]] = {}


def get_user_services(user_id: int) -> list[OutreachService]:
    """Все активные сервисы пользователя."""
    return list(active_outreach.get(user_id, {}).values())


def add_service(user_id: int, campaign_id: str, service: "OutreachService") -> None:
    """Добавляет сервис в глобальный реестр."""
    if user_id not in active_outreach:
        active_outreach[user_id] = {}
    active_outreach[user_id][campaign_id] = service


def remove_service(user_id: int, campaign_id: str) -> None:
    """Удаляет сервис из реестра."""
    if user_id in active_outreach:
        active_outreach[user_id].pop(campaign_id, None)
        if not active_outreach[user_id]:
            del active_outreach[user_id]
