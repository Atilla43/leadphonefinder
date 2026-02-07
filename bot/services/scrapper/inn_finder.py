"""Поиск ИНН компании по названию."""

import asyncio
import logging
import re
from typing import Optional

import aiohttp

from bot.services.scrapper.models import ScrapedCompany
from bot.services.inn_validator import validate_inn

logger = logging.getLogger(__name__)


class InnFinder:
    """Сервис поиска ИНН по названию компании."""

    # API endpoints для поиска
    DADATA_SUGGEST_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"
    EGRUL_NALOG_URL = "https://egrul.nalog.ru/search-result/"

    def __init__(
        self,
        dadata_token: Optional[str] = None,
        request_delay: float = 0.5,
    ) -> None:
        """
        Инициализация.

        Args:
            dadata_token: API токен DaData (опционально)
            request_delay: Задержка между запросами
        """
        self.dadata_token = dadata_token
        self.request_delay = request_delay
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получает или создаёт HTTP сессию."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self) -> None:
        """Закрывает HTTP сессию."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def find_inn(
        self,
        company_name: str,
        address: Optional[str] = None,
    ) -> Optional[str]:
        """
        Ищет ИНН по названию компании.

        Args:
            company_name: Название компании
            address: Адрес для уточнения (опционально)

        Returns:
            ИНН или None
        """
        if not company_name:
            return None

        # Сначала пробуем DaData (если есть токен)
        if self.dadata_token:
            inn = await self._search_dadata(company_name, address)
            if inn:
                return inn

        # Fallback: парсинг ЕГРЮЛ (бесплатно, но медленнее)
        inn = await self._search_egrul(company_name)
        if inn:
            return inn

        return None

    async def _search_dadata(
        self,
        company_name: str,
        address: Optional[str] = None,
    ) -> Optional[str]:
        """
        Поиск через DaData API.

        Требует API токен (бесплатно до 10к запросов/день).
        """
        if not self.dadata_token:
            return None

        try:
            session = await self._get_session()

            query = company_name
            if address:
                # Добавляем город для уточнения
                city_match = re.search(r'(москва|санкт-петербург|[\w-]+)', address.lower())
                if city_match:
                    query = f"{company_name} {city_match.group(1)}"

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Token {self.dadata_token}",
            }

            payload = {
                "query": query,
                "count": 5,
            }

            async with session.post(
                self.DADATA_SUGGEST_URL,
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    logger.warning(f"DaData API error: {response.status}")
                    return None

                data = await response.json()
                suggestions = data.get("suggestions", [])

                if not suggestions:
                    return None

                # Берём первый результат
                first = suggestions[0]
                inn = first.get("data", {}).get("inn")

                if inn and validate_inn(inn):
                    logger.debug(f"Found INN via DaData: {company_name} -> {inn}")
                    return inn

        except Exception as e:
            logger.error(f"DaData search error: {e}")

        return None

    async def _search_egrul(self, company_name: str) -> Optional[str]:
        """
        Поиск через ЕГРЮЛ (nalog.ru).

        Бесплатный метод, но требует парсинг HTML.
        """
        try:
            session = await self._get_session()

            # Нормализуем название
            clean_name = re.sub(r'[«»"\'\"\"\']', '', company_name)
            clean_name = re.sub(r'\s+', ' ', clean_name).strip()

            # Первый запрос - инициация поиска
            search_url = "https://egrul.nalog.ru/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "Accept": "application/json, text/javascript, */*",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            # Запрос на поиск
            payload = {
                "vyession": "1",
                "query": clean_name,
                "region": "",
            }

            async with session.post(
                search_url,
                headers=headers,
                data=payload,
            ) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                token = data.get("t")

                if not token:
                    return None

            # Ждём результаты
            await asyncio.sleep(self.request_delay)

            # Получаем результаты
            result_url = f"https://egrul.nalog.ru/search-result/{token}"

            async with session.get(result_url, headers=headers) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                rows = data.get("rows", [])

                if not rows:
                    return None

                # Берём первый результат
                first = rows[0]
                inn = first.get("i")  # ИНН в поле 'i'

                if inn and validate_inn(str(inn)):
                    logger.debug(f"Found INN via EGRUL: {company_name} -> {inn}")
                    return str(inn)

        except Exception as e:
            logger.debug(f"EGRUL search error for '{company_name}': {e}")

        return None

    async def enrich_companies(
        self,
        companies: list[ScrapedCompany],
        progress_callback=None,
    ) -> tuple[int, int]:
        """
        Добавляет ИНН к списку компаний.

        Args:
            companies: Список компаний
            progress_callback: Callback для отслеживания прогресса

        Returns:
            Кортеж (найдено ИНН, не найдено)
        """
        found = 0
        not_found = 0

        for i, company in enumerate(companies):
            # Пропускаем если ИНН уже есть
            if company.inn and validate_inn(company.inn):
                found += 1
                continue

            # Ищем ИНН
            inn = await self.find_inn(company.name, company.address)

            if inn:
                company.inn = inn
                found += 1
            else:
                not_found += 1

            # Callback прогресса
            if progress_callback:
                await progress_callback(i + 1, len(companies), company.name, inn)

            # Задержка между запросами
            await asyncio.sleep(self.request_delay)

        logger.info(f"INN enrichment: found {found}, not found {not_found}")
        return found, not_found
