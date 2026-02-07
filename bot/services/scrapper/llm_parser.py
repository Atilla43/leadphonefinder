"""LLM-парсер для сложных запросов (OpenAI, GigaChat)."""

import logging
import json
from typing import Optional
from dataclasses import dataclass

import aiohttp

from bot.services.scrapper.query_parser import ParsedQuery, CITIES

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Конфигурация LLM."""
    provider: str  # "openai", "gigachat", "yandexgpt"
    api_key: str
    model: str = "gpt-4o-mini"  # или "GigaChat", "yandexgpt-lite"
    base_url: Optional[str] = None  # Для совместимых API


SYSTEM_PROMPT = """Ты парсер поисковых запросов для поиска компаний в России.

Твоя задача: извлечь из запроса пользователя категорию бизнеса и город.

Отвечай ТОЛЬКО валидным JSON в формате:
{"category": "категория", "location": "город"}

Примеры:
- "рестораны Сочи" → {"category": "рестораны", "location": "Сочи"}
- "где поесть в мск" → {"category": "рестораны", "location": "Москва"}
- "автосервис питер" → {"category": "автосервисы", "location": "Санкт-Петербург"}
- "кафешки в казане" → {"category": "кафе", "location": "Казань"}
- "ремонт машин екб" → {"category": "автосервисы", "location": "Екатеринбург"}
- "найти парикмахерскую в новосибе" → {"category": "салоны красоты", "location": "Новосибирск"}
- "стоматология нижний" → {"category": "стоматологии", "location": "Нижний Новгород"}

Если не можешь определить категорию или город, верни null для этого поля.
Всегда нормализуй названия городов (мск→Москва, спб→Санкт-Петербург, питер→Санкт-Петербург, екб→Екатеринбург).
"""


class LLMQueryParser:
    """Парсер запросов с использованием LLM."""

    def __init__(self, config: LLMConfig) -> None:
        """
        Инициализация LLM парсера.

        Args:
            config: Конфигурация LLM провайдера
        """
        self.config = config
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

    async def parse(self, query: str) -> Optional[ParsedQuery]:
        """
        Парсит запрос с помощью LLM.

        Args:
            query: Текстовый запрос пользователя

        Returns:
            ParsedQuery или None при ошибке
        """
        if self.config.provider == "openai":
            return await self._parse_openai(query)
        elif self.config.provider == "gigachat":
            return await self._parse_gigachat(query)
        elif self.config.provider == "yandexgpt":
            return await self._parse_yandexgpt(query)
        else:
            logger.error(f"Unknown LLM provider: {self.config.provider}")
            return None

    async def _parse_openai(self, query: str) -> Optional[ParsedQuery]:
        """Парсинг через OpenAI API (или совместимые)."""
        try:
            session = await self._get_session()

            base_url = self.config.base_url or "https://api.openai.com/v1"

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                "temperature": 0.1,  # Низкая температура для детерминированности
                "max_tokens": 100,
            }

            async with session.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"OpenAI API error: {response.status} - {error}")
                    return None

                data = await response.json()
                content = data["choices"][0]["message"]["content"]

                return self._parse_json_response(query, content)

        except Exception as e:
            logger.error(f"OpenAI parsing error: {e}")
            return None

    async def _parse_gigachat(self, query: str) -> Optional[ParsedQuery]:
        """Парсинг через GigaChat API (Сбер)."""
        try:
            session = await self._get_session()

            # GigaChat требует OAuth токен
            # Сначала получаем access token
            auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

            auth_headers = {
                "Authorization": f"Basic {self.config.api_key}",
                "RqUID": "unique-request-id",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            async with session.post(
                auth_url,
                headers=auth_headers,
                data={"scope": "GIGACHAT_API_PERS"},
                ssl=False,  # GigaChat требует отключения SSL верификации
            ) as auth_response:
                if auth_response.status != 200:
                    logger.error(f"GigaChat auth error: {auth_response.status}")
                    return None

                auth_data = await auth_response.json()
                access_token = auth_data["access_token"]

            # Теперь делаем запрос к API
            api_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.config.model or "GigaChat",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                "temperature": 0.1,
                "max_tokens": 100,
            }

            async with session.post(
                api_url,
                headers=headers,
                json=payload,
                ssl=False,
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"GigaChat API error: {response.status} - {error}")
                    return None

                data = await response.json()
                content = data["choices"][0]["message"]["content"]

                return self._parse_json_response(query, content)

        except Exception as e:
            logger.error(f"GigaChat parsing error: {e}")
            return None

    async def _parse_yandexgpt(self, query: str) -> Optional[ParsedQuery]:
        """Парсинг через YandexGPT API."""
        try:
            session = await self._get_session()

            # YandexGPT API
            api_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

            headers = {
                "Authorization": f"Api-Key {self.config.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "modelUri": f"gpt://{self.config.base_url or 'folder_id'}/{self.config.model or 'yandexgpt-lite'}",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.1,
                    "maxTokens": 100,
                },
                "messages": [
                    {"role": "system", "text": SYSTEM_PROMPT},
                    {"role": "user", "text": query},
                ],
            }

            async with session.post(
                api_url,
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"YandexGPT API error: {response.status} - {error}")
                    return None

                data = await response.json()
                content = data["result"]["alternatives"][0]["message"]["text"]

                return self._parse_json_response(query, content)

        except Exception as e:
            logger.error(f"YandexGPT parsing error: {e}")
            return None

    def _parse_json_response(self, original_query: str, content: str) -> Optional[ParsedQuery]:
        """Парсит JSON ответ от LLM."""
        try:
            # Очищаем от возможных markdown блоков
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            data = json.loads(content)

            category = data.get("category", "")
            location = data.get("location", "")

            if not category or not location:
                return None

            # Ищем координаты города
            location_lower = location.lower()
            location_data = None

            for city_name, city_data in CITIES.items():
                if city_name == location_lower or location_lower in city_name:
                    location_data = city_data
                    break

            result = ParsedQuery(
                original=original_query,
                category=category,
                location=location,
                used_llm=True,
            )

            if location_data:
                result.latitude = location_data["lat"]
                result.longitude = location_data["lon"]
                result.bbox = location_data["bbox"]

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {content} - {e}")
            return None


def create_openai_parser(api_key: str, model: str = "gpt-4o-mini") -> LLMQueryParser:
    """Создаёт парсер на базе OpenAI."""
    config = LLMConfig(
        provider="openai",
        api_key=api_key,
        model=model,
    )
    return LLMQueryParser(config)


def create_gigachat_parser(api_key: str, model: str = "GigaChat") -> LLMQueryParser:
    """Создаёт парсер на базе GigaChat (Сбер)."""
    config = LLMConfig(
        provider="gigachat",
        api_key=api_key,
        model=model,
    )
    return LLMQueryParser(config)


def create_yandexgpt_parser(
    api_key: str,
    folder_id: str,
    model: str = "yandexgpt-lite"
) -> LLMQueryParser:
    """Создаёт парсер на базе YandexGPT."""
    config = LLMConfig(
        provider="yandexgpt",
        api_key=api_key,
        model=model,
        base_url=folder_id,
    )
    return LLMQueryParser(config)
