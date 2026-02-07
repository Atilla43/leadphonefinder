"""API клиент для Dyxless (Sherlock API).

Документация: https://dyxless.b-cdn.net/api.html
Base URL: https://api-dyxless.cfd/query
Лимит: 100 запросов за 15 минут на IP
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import aiohttp

from bot.utils.config import settings

logger = logging.getLogger(__name__)

# Regex для извлечения телефонов из данных
PHONE_PATTERN = re.compile(r"\+?[78][\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")


class SherlockAPIError(Exception):
    """Базовая ошибка API."""
    pass


class RateLimitError(SherlockAPIError):
    """Превышен лимит запросов (100 за 15 минут)."""

    def __init__(self, retry_after: int = 900):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")


class AuthenticationError(SherlockAPIError):
    """Ошибка аутентификации (неверный токен)."""
    pass


class InsufficientBalanceError(SherlockAPIError):
    """Недостаточный баланс."""
    pass


class NotFoundError(SherlockAPIError):
    """Данные не найдены."""
    pass


@dataclass
class SherlockResponse:
    """Ответ от Dyxless API."""

    query: str
    found: bool
    phones: list[str]
    emails: list[str] = None
    names: list[str] = None
    addresses: list[str] = None
    sources: list[str] = None  # baseName из ответа (источники данных)
    raw_data: Optional[dict] = None
    counts: int = 0

    def __post_init__(self):
        if self.emails is None:
            self.emails = []
        if self.names is None:
            self.names = []
        if self.addresses is None:
            self.addresses = []
        if self.sources is None:
            self.sources = []


class BaseSherlockClient(ABC):
    """Абстрактный базовый класс для клиентов."""

    @abstractmethod
    async def query(self, search_query: str) -> Optional[SherlockResponse]:
        """Запрос данных."""
        pass

    @abstractmethod
    async def query_with_retry(
        self, search_query: str, retries: int = 3
    ) -> Optional[SherlockResponse]:
        """Запрос с повторными попытками."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Закрытие соединения."""
        pass


class SherlockAPIClient(BaseSherlockClient):
    """
    HTTP API клиент для Dyxless.

    API Documentation: https://dyxless.b-cdn.net/api.html

    Endpoints:
        POST /query — основной поиск (standart: 2₽, telegram: 10₽)
        POST /query/inn-emails — email по ИНН (ограниченный доступ)

    Rate limit: 100 запросов за 15 минут на IP

    Пример использования:
        client = SherlockAPIClient(api_url, token)
        response = await client.query("7707083893")
        if response and response.found:
            print(response.phones)
    """

    # Стоимость запросов
    COST_STANDARD = 2  # рубля
    COST_TELEGRAM = 10  # рублей

    def __init__(
        self,
        api_url: str,
        token: str,
        timeout: float = 30.0,
        max_concurrent: int = 5,
        query_type: str = "standart",
    ):
        """
        Args:
            api_url: Base URL API (https://api-dyxless.cfd)
            token: API токен от бота
            timeout: Таймаут запроса в секундах
            max_concurrent: Максимум параллельных запросов
            query_type: Тип запроса ("standart" или "telegram")
        """
        self.api_url = api_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.query_type = query_type
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy initialization сессии."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "LeadPhoneFinder/1.0",
                },
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
        return self._session

    async def query(
        self,
        search_query: str,
        query_type: Optional[str] = None,
    ) -> Optional[SherlockResponse]:
        """
        Запрос данных через API.

        Args:
            search_query: Строка поиска (ИНН, телефон, email и т.д.)
            query_type: Тип запроса ("standart" или "telegram"), по умолчанию из конструктора

        Returns:
            SherlockResponse с данными или None

        Raises:
            RateLimitError: Превышен лимит запросов (100/15мин)
            AuthenticationError: Неверный токен
            InsufficientBalanceError: Недостаточный баланс
            SherlockAPIError: Другие ошибки API
        """
        async with self._semaphore:
            session = await self._get_session()

            url = f"{self.api_url}/query"
            payload = {
                "token": self.token,
                "query": search_query,
            }

            # Добавляем тип запроса если не standart
            effective_type = query_type or self.query_type
            if effective_type and effective_type != "standart":
                payload["type"] = effective_type

            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_response(search_query, data)

                    elif response.status == 400:
                        error_text = await response.text()
                        logger.error(f"Bad request: {error_text}")
                        raise SherlockAPIError(f"Bad request: {error_text}")

                    elif response.status == 401:
                        raise AuthenticationError("Invalid token")

                    elif response.status == 403:
                        error_text = await response.text()
                        if "balance" in error_text.lower() or "баланс" in error_text.lower():
                            raise InsufficientBalanceError("Insufficient balance")
                        raise SherlockAPIError(f"Forbidden: {error_text}")

                    elif response.status == 404:
                        return SherlockResponse(
                            query=search_query,
                            found=False,
                            phones=[],
                        )

                    elif response.status == 429:
                        # Rate limit: 100 запросов за 15 минут = 900 секунд
                        retry_after = int(response.headers.get("Retry-After", "900"))
                        raise RateLimitError(retry_after)

                    elif response.status == 500:
                        error_text = await response.text()
                        logger.error(f"Server error: {error_text}")
                        raise SherlockAPIError(f"Server error: {error_text}")

                    else:
                        error_text = await response.text()
                        logger.error(f"API error {response.status}: {error_text}")
                        raise SherlockAPIError(f"API returned {response.status}: {error_text}")

            except aiohttp.ClientError as e:
                logger.error(f"Network error querying API: {e}")
                raise SherlockAPIError(f"Network error: {e}")

    async def query_inn_emails(self, inn: str) -> Optional[SherlockResponse]:
        """
        Запрос email по ИНН (ограниченный доступ).

        Args:
            inn: ИНН компании или физлица

        Returns:
            SherlockResponse с email-ами или None
        """
        async with self._semaphore:
            session = await self._get_session()

            url = f"{self.api_url}/query/inn-emails"
            payload = {
                "token": self.token,
                "inn": inn,
            }

            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_email_response(inn, data)

                    elif response.status == 401:
                        raise AuthenticationError("Invalid token")

                    elif response.status == 403:
                        raise SherlockAPIError("Access denied to inn-emails endpoint")

                    elif response.status == 404:
                        return SherlockResponse(
                            query=inn,
                            found=False,
                            phones=[],
                            emails=[],
                        )

                    else:
                        error_text = await response.text()
                        raise SherlockAPIError(f"API returned {response.status}: {error_text}")

            except aiohttp.ClientError as e:
                raise SherlockAPIError(f"Network error: {e}")

    def _parse_response(self, query: str, data: dict) -> SherlockResponse:
        """
        Парсит ответ API.

        Формат ответа:
        {
            "status": true,
            "counts": 5,
            "data": [...]
        }
        """
        if not data.get("status", False):
            return SherlockResponse(query=query, found=False, phones=[], raw_data=data)

        counts = data.get("counts", 0)
        result_data = data.get("data", [])

        phones = []
        emails = []
        names = []
        addresses = []
        sources = []

        # Извлекаем данные из массива результатов
        if isinstance(result_data, list):
            for item in result_data:
                if isinstance(item, dict):
                    # Телефоны — проверяем несколько полей
                    for key in ("phone", "phones", "tel", "telephone", "mobile", "number"):
                        value = item.get(key)
                        if value and str(value).strip() not in ("", "0", "N"):
                            val_str = str(value).strip()
                            # Пропускаем email в поле number
                            if "@" in val_str:
                                continue
                            # Проверяем что это похоже на телефон (11 цифр, начинается с 7 или 8)
                            digits = re.sub(r"\D", "", val_str)
                            if len(digits) >= 10 and len(digits) <= 12:
                                if isinstance(value, list):
                                    phones.extend([str(v) for v in value])
                                else:
                                    phones.append(val_str)

                    # Email
                    for key in ("email", "emails", "mail"):
                        value = item.get(key)
                        if value and "@" in str(value):
                            if isinstance(value, list):
                                emails.extend(value)
                            else:
                                emails.append(str(value))

                    # Имена — проверяем несколько полей
                    for key in ("name", "full_name", "fio", "owner", "fullName"):
                        value = item.get(key)
                        if value and str(value).strip():
                            # Фильтруем мусор — слишком короткие или содержащие только цифры
                            name_str = str(value).strip()
                            if len(name_str) > 3 and not name_str.isdigit():
                                names.append(name_str)

                    # Адреса
                    for key in ("address", "addr"):
                        value = item.get(key)
                        if value and str(value).strip():
                            addr_str = str(value).strip()
                            # Фильтруем — адрес должен быть похож на адрес (содержать буквы и быть длинным)
                            if len(addr_str) > 10 and any(c.isalpha() for c in addr_str):
                                addresses.append(addr_str)

                    # Источники (baseName)
                    base_name = item.get("baseName")
                    if base_name and str(base_name).strip():
                        sources.append(str(base_name).strip())

                elif isinstance(item, str):
                    # Пробуем извлечь телефон из строки
                    found_phones = PHONE_PATTERN.findall(item)
                    phones.extend(found_phones)

        # Дедупликация и нормализация
        phones = list(dict.fromkeys(self._normalize_phones(phones)))
        emails = list(dict.fromkeys(emails))
        names = list(dict.fromkeys(names))
        addresses = list(dict.fromkeys(addresses))
        sources = list(dict.fromkeys(sources))

        return SherlockResponse(
            query=query,
            found=bool(phones or emails or names),
            phones=phones,
            emails=emails,
            names=names,
            addresses=addresses,
            sources=sources,
            raw_data=data,
            counts=counts,
        )

    def _parse_email_response(self, inn: str, data: dict) -> SherlockResponse:
        """Парсит ответ от /query/inn-emails."""
        if not data.get("status", False):
            return SherlockResponse(query=inn, found=False, phones=[], emails=[])

        result_data = data.get("data", [])
        emails = []

        if isinstance(result_data, list):
            for item in result_data:
                if isinstance(item, dict):
                    email = item.get("email") or item.get("mail")
                    if email:
                        emails.append(email)
                elif isinstance(item, str) and "@" in item:
                    emails.append(item)

        return SherlockResponse(
            query=inn,
            found=bool(emails),
            phones=[],
            emails=list(dict.fromkeys(emails)),
            raw_data=data,
        )

    def _normalize_phones(self, phones: list[str]) -> list[str]:
        """Нормализует телефоны в формат +7XXXXXXXXXX."""
        normalized = []
        for phone in phones:
            # Убираем всё кроме цифр
            digits = re.sub(r"\D", "", phone)
            if len(digits) == 11:
                if digits.startswith("8"):
                    digits = "7" + digits[1:]
                normalized.append(f"+{digits}")
            elif len(digits) == 10:
                normalized.append(f"+7{digits}")
        return normalized

    async def query_with_retry(
        self,
        search_query: str,
        retries: int = 3,
        backoff_factor: float = 2.0,
    ) -> Optional[SherlockResponse]:
        """
        Запрос с автоматическими повторами при ошибках.

        Args:
            search_query: Строка поиска
            retries: Количество попыток
            backoff_factor: Множитель задержки между попытками

        Returns:
            SherlockResponse или None

        Raises:
            RateLimitError: При исчерпании лимита (пробрасывается наверх)
            AuthenticationError: При неверном токене
            InsufficientBalanceError: При недостаточном балансе
        """
        last_error = None

        for attempt in range(retries):
            try:
                return await self.query(search_query)

            except (RateLimitError, AuthenticationError, InsufficientBalanceError):
                # Критические ошибки — пробрасываем сразу
                raise

            except SherlockAPIError as e:
                last_error = e
                if attempt < retries - 1:
                    wait_time = (backoff_factor ** attempt) * 1.0
                    logger.warning(
                        f"API error for {search_query}, "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)

        if last_error:
            logger.error(f"All retries failed for {search_query}: {last_error}")

        return None

    async def batch_query(
        self,
        queries: list[str],
        progress_callback=None,
        delay_between: float = 1.0,
    ) -> list[SherlockResponse]:
        """
        Пакетный запрос для списка запросов.

        Args:
            queries: Список запросов (ИНН, телефоны и т.д.)
            progress_callback: async callback(current, total)
            delay_between: Задержка между запросами (антибан)

        Returns:
            Список ответов
        """
        results = []

        for i, q in enumerate(queries):
            try:
                response = await self.query_with_retry(q)
                results.append(
                    response or SherlockResponse(query=q, found=False, phones=[])
                )
            except RateLimitError as e:
                logger.warning(f"Rate limit hit at {i}/{len(queries)}, waiting {e.retry_after}s")
                # Добавляем пустые ответы для оставшихся
                for remaining in queries[i:]:
                    results.append(SherlockResponse(query=remaining, found=False, phones=[]))
                break
            except InsufficientBalanceError:
                logger.error("Insufficient balance, stopping batch")
                for remaining in queries[i:]:
                    results.append(SherlockResponse(query=remaining, found=False, phones=[]))
                break

            if progress_callback:
                await progress_callback(i + 1, len(queries))

            # Задержка между запросами
            if i < len(queries) - 1:
                await asyncio.sleep(delay_between)

        return results

    async def close(self) -> None:
        """Закрывает HTTP сессию."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None


# Глобальный клиент
_sherlock_api_client: Optional[SherlockAPIClient] = None


def is_api_configured() -> bool:
    """Проверяет, настроен ли API."""
    return bool(settings.sherlock_api_url and settings.sherlock_api_key)


async def get_sherlock_api_client() -> Optional[SherlockAPIClient]:
    """
    Возвращает API клиент если настроен.

    Returns:
        SherlockAPIClient или None если API не настроен
    """
    global _sherlock_api_client

    if not is_api_configured():
        return None

    if _sherlock_api_client is None:
        _sherlock_api_client = SherlockAPIClient(
            api_url=settings.sherlock_api_url,
            token=settings.sherlock_api_key,
        )
        logger.info("Dyxless API client initialized")

    return _sherlock_api_client


async def close_api_client() -> None:
    """Закрывает глобальный API клиент."""
    global _sherlock_api_client
    if _sherlock_api_client:
        await _sherlock_api_client.close()
        _sherlock_api_client = None
