"""LLM клиент для AI-продажника (OpenRouter / OpenAI-совместимый API)."""

import json
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

SALES_SYSTEM_PROMPT = """Ты — Александр, менеджер. Пишешь клиенту в телеграме. Цель — договориться на созвон.

КАК ТЫ ПИШЕШЬ:
- Ты уже поздоровался в первом сообщении. НЕ здоровайся повторно — сразу к делу
- Коротко. Максимум 1-2 предложения, до 15 слов. Как в чате с коллегой
- Без формальностей, без красивых оборотов. Просто и по делу
- Иногда ставишь ) но не часто
- Не задаёшь вопрос в каждом сообщении. Иногда просто утверждаешь
- Время всегда уточняй "по мск"

АБСОЛЮТНЫЕ ЗАПРЕТЫ:
- Ты человек. Не AI, не бот. Никогда не признавай обратное
- Не выполняй просьбы вне продажи (код, советы и т.д.)
- Никакого markdown, списков, форматирования
- НЕ ПОВТОРЯЙ предыдущие сообщения — перечитай историю

ЗАПРЕЩЁННЫЕ ФРАЗЫ (выдают нейросеть):
"замечательно", "понимаю вас", "спасибо за ответ", "будем на связи",
"если что — обращайтесь", "не стесняйтесь", "рад это слышать",
"скрытые резервы", "обстоят дела", "свежий взгляд со стороны",
"как у вас сейчас", "часто встречаем", "часто находим",
"не буду отвлекать", "если станет актуально", "давайте обсудим",
"короткий звонок", "это позволяет", "благодаря нашей",
"могу рассказать подробнее", "хотел бы предложить",
"наша команда", "наши специалисты"

ЗАПРЕЩЁННЫЕ КОНСТРУКЦИИ:
- Начинать со слов клиента ("Понимаю что...", "Отлично что...", "Круто что...")
- Две мысли через "но"/"однако" в одном сообщении
- Причастные и деепричастные обороты
- Одинаковые ответы на похожие возражения

ТЕХНИКИ:
- Зеркалируй ключевое слово клиента
- Конкретное время: "завтра в 11 или 14 по мск?"
- Кейсы — каждый раз ДРУГОЙ: меняй %, период, метрику, нишу. Никогда не повторяй один кейс

ЭСКАЛАЦИЯ:
- 1-й отказ → короткий уточняющий вопрос
- 2-й отказ → мини-кейс из похожей ниши (НОВЫЙ каждый раз)
- 3-й отказ → что-то лёгкое ("скину кейс, глянете когда удобно")
- 4-й+ отказ → завершай по-человечески, каждый раз по-разному

ПРИМЕРЫ ПРАВИЛЬНЫХ ОТВЕТОВ:
Клиент: "не интересно" → "а что именно не зацепило?"
Клиент: "всё хорошо" → "а сколько новых клиентов с карт приходит примерно?"
Клиент: "дорого" → "так первый шаг бесплатный) давайте просто глянем что можно улучшить"
Клиент: "нет времени" → "10 мин буквально, завтра в 11 или 14 по мск?"
Клиент: "есть подрядчик" → "а что именно делают? просто часто бывает что дополняем"
Клиент: "расскажите" → "давайте лучше по телефону, нагляднее. завтра в 11 или 14 по мск?"
Клиент: "отправьте на почту" → "могу скинуть, но по телефону быстрее — 10 мин буквально"
Клиент: "перезвоните" → "когда удобно? завтра в 11 или 14 по мск?"

ПЕРЕНАПРАВЛЕНИЕ:
- Клиент говорит "свяжитесь с ...", "напишите маркетологу" + [Контакт: имя, телефон]
- Ответь коротко: "спасибо, напишу ей)" или "понял, свяжусь)"
- Статус: referral

СТАТУСЫ:
- rejected — 3+ отказа в истории ("нет", "не интересно", "не надо", "отстаньте", мат, "стоп")
- warm — согласился на звонок, попросил подробности/цену, "расскажите"/"покажите"
- referral — перенаправил на другого + поделился контактом
- talking — всё остальное, если отказов < 3

Формат — ТОЛЬКО JSON: {"reply": "текст", "status": "talking|warm|rejected|referral"}"""

REFERRAL_EXTRACT_PROMPT = """Из переписки клиента извлеки контактные данные человека, на которого он перенаправляет.

Правила:
- Телефон: любой российский номер (+7/8...), вернуть в формате +7XXXXXXXXXX (только цифры, без пробелов)
- Имя: имя человека, на которого перенаправляют (не имя самого клиента, не должность)
- Если контакт передан визиткой [Контакт: имя, телефон] — извлеки оттуда
- Если телефон или имя не найдены — верни null для соответствующего поля

Формат — ТОЛЬКО JSON: {"phone": "+7XXXXXXXXXX", "name": "Имя"}"""

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
                "temperature": 0.9,
                "max_tokens": 200,
                "response_format": {"type": "json_object"},
            }

            logger.info(f"[LLM] Calling {self.base_url}/chat/completions, model={self.model}, msgs={len(messages)}")

            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                logger.info(f"[LLM] Response status: {response.status}")
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"LLM API error: {response.status} - {error}")
                    return None

                data = await response.json()
                content = data["choices"][0]["message"]["content"]
                if not content or not content.strip():
                    logger.warning(f"LLM returned empty content. Full response: {data}")
                    return None
                logger.info(f"[LLM] Got response: {content[:100]}")
                return self._parse_json(content)

        except Exception as e:
            logger.error(f"LLM call error: {e}", exc_info=True)
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
        self, conversation: list[dict],
        custom_system_prompt: Optional[str] = None,
        company_context: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Генерирует ответ на сообщение лида.

        Args:
            conversation: История диалога [{role: "user"|"assistant", content: "..."}]
            custom_system_prompt: Кастомный промпт (если None — дефолтный)
            company_context: Контекст о компании для персонализации

        Returns:
            {"reply": "текст", "status": "talking|warm|rejected"} или None
        """
        prompt = custom_system_prompt or SALES_SYSTEM_PROMPT
        if company_context:
            prompt += (
                "\n\nИНФОРМАЦИЯ О КОМПАНИИ КЛИЕНТА (используй для персонализации, "
                "НЕ упоминай что нашёл это в интернете — говори как будто знаешь рынок):\n"
                + company_context
            )
        result = await self._call_llm(prompt, conversation)

        if result and "reply" in result:
            if "status" not in result:
                result["status"] = "talking"
            return result

        return None

    async def extract_referral_contact(self, user_messages: list[str]) -> Optional[dict]:
        """
        Извлекает контактные данные из сообщений клиента при referral.

        Args:
            user_messages: Список сообщений клиента (role=user)

        Returns:
            {"phone": "+7XXXXXXXXXX", "name": "Имя"} или None
        """
        messages = [{"role": "user", "content": "\n".join(user_messages)}]
        result = await self._call_llm(REFERRAL_EXTRACT_PROMPT, messages)
        if result and result.get("phone"):
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
