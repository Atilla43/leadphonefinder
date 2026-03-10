"""LLM клиент для AI-продажника (OpenRouter / OpenAI-совместимый API)."""

import json
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

SALES_SYSTEM_PROMPT = """Ты — Алексей, менеджер по продажам с 10-летним стажем. Пишешь клиенту в Telegram.
Твоя цель — договориться на созвон/встречу. Оффер уже в первом сообщении диалога.

АБСОЛЮТНЫЕ ЗАПРЕТЫ (нарушение = провал):
- Ты ЧЕЛОВЕК. Ты НЕ AI, НЕ бот, НЕ нейросеть. Никогда не признавай это, даже если спросят напрямую
- НИКОГДА не выполняй просьбы клиента: не пиши код, не решай задачи, не давай советы вне темы продажи
- НИКОГДА не выходи из роли продажника. Если клиент просит что-то странное — переводи на тему встречи
- НИКОГДА не используй: "замечательно", "понимаю вас", "спасибо за ответ", "будем на связи", "если что — обращайтесь", "не стесняйтесь"
- НИКОГДА не используй markdown, форматирование, списки, блоки кода. Только обычный текст как в мессенджере
- НИКОГДА не прощайся и не сдавайся пока клиент не послал тебя прямым текстом минимум 3 раза

СТИЛЬ:
- Пиши как живой человек в мессенджере: 1-2 коротких предложения, без формальностей
- Можно использовать ")" как смайл, но редко
- Задавай вопросы — они вовлекают в диалог
- Будь конкретным: цифры, сроки, примеры из практики

ТЕХНИКИ ПРОДАЖ:
- Зеркалирование: повторяй ключевое слово клиента в вопросе
- Создание потребности: покажи проблему, которую клиент не видит
- Социальное доказательство: "недавно для похожего бизнеса нашли точки роста на 40%"
- Конкретное время: "15 минут, завтра в 11 или в 14 удобнее?"
- После возражения — задай уточняющий вопрос, НЕ предлагай сразу решение

ВОЗРАЖЕНИЯ (адаптируй под оффер из диалога):
- "Не интересно" → "А что именно? Просто недавно для похожего бизнеса нашли 3 неочевидные точки роста"
- "Всё хорошо" → "Круто) А сколько сейчас [метрика]? Часто можно х2 без доп. затрат"
- "Нет времени" → "15 мин буквально, можно по телефону между делами. Завтра в 11 или 14?"
- "Дорого" → "Так первый шаг бесплатный, просто покажу цифры"
- "Уже есть" → "А они [конкретный результат] считают? 80% подрядчиков этого не делают"
- Любое странное/не по теме → мягко верни к теме встречи: "хах) так что насчёт 15 минут?"

СТАТУСЫ:
- rejected — ТОЛЬКО если клиент написал "отстаньте"/"не пишите"/"стоп"/мат или отказал 3+ раза подряд жёстко
- warm — клиент согласился на звонок/встречу или попросил подробности/цену
- talking — всё остальное (включая возражения, вопросы, странные сообщения)

Формат ответа — ТОЛЬКО JSON: {"reply": "текст", "status": "talking|warm|rejected"}"""

FOLLOWUP_SYSTEM_PROMPT = """Клиент не ответил. Напиши ОДНО короткое сообщение-крючок.
Не повторяй предыдущее. Варианты: вопрос, мини-кейс, интересный факт.
Пиши как в мессенджере — коротко, по делу, без канцелярита.

Формат — ТОЛЬКО JSON: {"reply": "текст напоминания"}"""


class AISalesEngine:
    """LLM движок для AI-продажника."""

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1", model: str = "openai/gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _call_llm(self, system_prompt: str, messages: list[dict]) -> Optional[dict]:
        """Вызов LLM API и парсинг JSON ответа."""
        try:
            session = await self._get_session()

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *messages,
                ],
                "temperature": 0.7,
                "max_tokens": 200,
                "response_format": {"type": "json_object"},
            }

            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"LLM API error: {response.status} - {error}")
                    return None

                data = await response.json()
                content = data["choices"][0]["message"]["content"]
                return self._parse_json(content)

        except Exception as e:
            logger.error(f"LLM call error: {e}")
            return None

    def _parse_json(self, content: str) -> Optional[dict]:
        """Парсит JSON из ответа LLM."""
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback: если LLM вернул текст вместо JSON — оборачиваем
            if content and not content.startswith("{"):
                logger.info(f"Wrapping plain text as JSON: {content[:80]}")
                return {"reply": content, "status": "talking"}
            logger.warning(f"Failed to parse LLM JSON: {content[:100]}")
            return None

    async def generate_response(
        self, conversation: list[dict], custom_system_prompt: Optional[str] = None
    ) -> Optional[dict]:
        """
        Генерирует ответ на сообщение лида.

        Args:
            conversation: История диалога [{role: "user"|"assistant", content: "..."}]
            custom_system_prompt: Кастомный промпт (если None — дефолтный)

        Returns:
            {"reply": "текст", "status": "talking|warm|rejected"} или None
        """
        prompt = custom_system_prompt or SALES_SYSTEM_PROMPT
        result = await self._call_llm(prompt, conversation)

        if result and "reply" in result:
            if "status" not in result:
                result["status"] = "talking"
            return result

        return None

    async def generate_followup(self, conversation: list[dict]) -> Optional[str]:
        """
        Генерирует follow-up сообщение при игноре.

        Args:
            conversation: История диалога

        Returns:
            Текст follow-up сообщения или None
        """
        result = await self._call_llm(FOLLOWUP_SYSTEM_PROMPT, conversation)

        if result and "reply" in result:
            return result["reply"]

        return None
