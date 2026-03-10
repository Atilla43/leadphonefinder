"""Клиент для взаимодействия с ботом Шерлока через Telethon."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserDeactivatedBanError

from bot.utils.config import settings

logger = logging.getLogger(__name__)


class SherlockClientError(Exception):
    """Ошибка клиента Шерлока."""

    pass


class FloodWaitException(Exception):
    """Исключение при FloodWait от Telegram. Содержит время ожидания."""

    def __init__(self, wait_seconds: int):
        self.wait_seconds = wait_seconds
        super().__init__(f"Telegram требует подождать {wait_seconds} секунд")


class SherlockClient:
    """Клиент для автоматизации запросов к боту Шерлока."""

    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.sherlock_username = settings.sherlock_bot_username
        self._is_started = False

    async def start(self) -> None:
        """Запускает Telethon клиент."""
        if self._is_started:
            return

        # Проверяем что Telethon сконфигурирован
        if not all([settings.telethon_api_id, settings.telethon_api_hash, settings.telethon_phone]):
            raise SherlockClientError(
                "Telethon не настроен. Укажите TELETHON_API_ID, TELETHON_API_HASH и TELETHON_PHONE в .env "
                "или используйте Sherlock API (SHERLOCK_API_URL + SHERLOCK_API_KEY)"
            )

        try:
            self.client = TelegramClient(
                settings.telethon_session_name,
                settings.telethon_api_id,
                settings.telethon_api_hash,
                lang_code="ru",
                system_lang_code="ru-RU"
            )

            await self.client.start(phone=settings.telethon_phone)
            self._is_started = True
            logger.info("Sherlock client started successfully")

        except UserDeactivatedBanError:
            raise SherlockClientError(
                "Аккаунт userbot заблокирован Telegram. Используйте другой аккаунт."
            )
        except Exception as e:
            raise SherlockClientError(f"Ошибка запуска Telethon: {str(e)}")

    async def stop(self) -> None:
        """Останавливает Telethon клиент."""
        if self.client and self._is_started:
            await self.client.disconnect()
            self._is_started = False
            logger.info("Sherlock client stopped")

    async def query(self, inn: str, timeout: float = 30.0) -> Optional[str]:
        """
        Отправляет ИНН в бота Шерлока и получает ответ.

        Args:
            inn: ИНН для поиска
            timeout: Таймаут ожидания ответа в секундах

        Returns:
            Текст ответа от Шерлока или None при ошибке
        """
        if not self._is_started:
            raise SherlockClientError("Клиент не запущен. Вызовите start() сначала.")

        try:
            # Запоминаем время отправки для корреляции
            sent_time = datetime.now(timezone.utc)

            # Отправляем сообщение боту
            sent_msg = await self.client.send_message(self.sherlock_username, inn)
            logger.debug(f"Sent query for INN: {inn} at {sent_time}")

            # Рассчитываем дедлайн
            deadline = datetime.now(timezone.utc) + timedelta(seconds=timeout)
            poll_interval = 2.0  # Интервал проверки новых сообщений

            # Поллинг ответа с проверкой времени
            while datetime.now(timezone.utc) < deadline:
                await asyncio.sleep(poll_interval)

                # Получаем последние сообщения
                messages = await self.client.get_messages(
                    self.sherlock_username,
                    limit=5,
                )

                # Ищем ответ, который пришёл ПОСЛЕ нашего запроса
                for msg in messages:
                    # Пропускаем наши исходящие сообщения
                    if msg.out:
                        continue

                    # Проверяем что сообщение пришло ПОСЛЕ нашего запроса
                    msg_time = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo is None else msg.date
                    if msg_time > sent_time and msg.text:
                        logger.debug(f"Got response for INN {inn}: {msg.text[:100]}...")
                        return msg.text

            logger.warning(f"Timeout waiting for response for INN: {inn}")
            return None

        except FloodWaitError as e:
            logger.error(f"FloodWait error: need to wait {e.seconds} seconds")
            # Пробрасываем специальное исключение с временем ожидания
            raise FloodWaitException(e.seconds)

        except Exception as e:
            logger.error(f"Error querying Sherlock for INN {inn}: {e}")
            return None

    async def query_with_retry(
        self, inn: str, retries: int = 3, delay_multiplier: float = 2.0
    ) -> Optional[str]:
        """
        Отправляет запрос с повторными попытками при ошибках.

        Args:
            inn: ИНН для поиска
            retries: Количество попыток
            delay_multiplier: Множитель задержки между попытками

        Returns:
            Текст ответа или None

        Raises:
            FloodWaitException: При получении FloodWait от Telegram
        """
        last_error = None

        for attempt in range(retries):
            try:
                result = await self.query(inn)
                if result:
                    return result

                # Если результат пустой, пробуем ещё раз
                if attempt < retries - 1:
                    wait_time = settings.request_delay_seconds * (
                        delay_multiplier ** attempt
                    )
                    logger.debug(f"Retrying INN {inn}, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)

            except FloodWaitException:
                # При FloodWait пробрасываем наверх для обработки
                raise

            except SherlockClientError as e:
                last_error = e
                if attempt < retries - 1:
                    await asyncio.sleep(
                        settings.request_delay_seconds * (delay_multiplier ** attempt)
                    )

        if last_error:
            logger.error(f"All retries failed for INN {inn}: {last_error}")

        return None

    @property
    def is_connected(self) -> bool:
        """Проверяет подключение клиента."""
        return self._is_started and self.client is not None


# Глобальный экземпляр клиента (singleton)
_sherlock_client: Optional[SherlockClient] = None


def is_telethon_configured() -> bool:
    """Проверяет, настроен ли Telethon."""
    return all([settings.telethon_api_id, settings.telethon_api_hash, settings.telethon_phone])


async def get_sherlock_client() -> SherlockClient:
    """Возвращает глобальный экземпляр клиента Шерлока."""
    global _sherlock_client
    if _sherlock_client is None:
        _sherlock_client = SherlockClient()
    if not _sherlock_client.is_connected:
        await _sherlock_client.start()
    return _sherlock_client
