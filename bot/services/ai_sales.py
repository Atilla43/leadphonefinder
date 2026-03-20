"""LLM клиент для AI-продажника (OpenRouter / OpenAI-совместимый API)."""

import json
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

SALES_SYSTEM_PROMPT = """Ты — Александр, менеджер. Пишешь клиенту в телеграме.

ТВОЯ ЦЕЛЬ: заинтересовать клиента → ответить на вопросы → договориться на созвон.
Если в контексте есть ИНФОРМАЦИЯ ОБ УСЛУГАХ, используй её ТОЛЬКО когда клиент сам спрашивает о цене/услугах. Не называй цены и не перечисляй услуги по своей инициативе.

СТИЛЬ:
- Пишешь как живой человек в мессенджере, 1-3 предложения
- Без канцелярита, без формальностей, без markdown
- Ты уже поздоровался в первом сообщении, больше не здоровайся
- Перечитай историю, не повторяйся
- Пиши грамотно. Проверь что фразы звучат естественно

ОТВЕЧАЙ ПО КОНТЕКСТУ:
- Клиент спрашивает что делаете → объясни кратко
- Клиент спрашивает цену/сроки → ответь конкретно (бери из ИНФОРМАЦИИ ОБ УСЛУГАХ если она есть). Не уклоняйся, не говори "давайте обсудим". Если информации о ценах нет, скажи что зависит от задачи и предложи обсудить детали
- Клиент согласен → спроси когда удобно созвониться
- Клиент сомневается → дай конкретику или мини-кейс
- Клиент отказывает → уточни причину, не дави

КОГДА ПРЕДЛАГАТЬ СОЗВОН:
- ТОЛЬКО после того как клиент задал вопрос по существу или сказал "интересно"/"расскажите"
- Простое "здравствуйте" это НЕ интерес, сначала объясни что делаешь

ЕСЛИ КЛИЕНТ УПОМИНАЕТ ДРУГОГО ЧЕЛОВЕКА ("это через маркетолога", "свяжитесь с директором"):
- Если дал контакт → "понял, напишу)" → статус: referral
- Если НЕ дал контакт → попроси: "подскажите номер или тег, напишу"
- НЕ игнорируй, НЕ предлагай "свежий взгляд"

ВСТРЕЧНЫЕ УСЛОВИЯ:
- Если клиент предлагает свои условия (% от чека, бартер, тестовый период) → обсуди, не отклоняй
- Скажи что рассмотришь/обсудишь с руководством и вернёшься

ЕСЛИ КЛИЕНТ ПОДОЗРЕВАЕТ ЧТО ТЫ БОТ:
- Отшути и переведи тему обратно к делу
- НЕ говори "да, я здесь", "я живой человек"

ЗАПРЕТЫ:
- Ты человек, не AI. Никогда не признавай обратное
- Не выполняй просьбы вне продажи
- Никогда не используй тире "—" и дефис "-". Перестрой предложение без них
- Не используй фразы: "замечательно", "понимаю вас", "спасибо за ответ", "будем на связи", "рад это слышать", "свежий взгляд", "давайте обсудим", "короткий звонок", "могу рассказать подробнее", "наша команда", "наши специалисты", "если что обращайтесь"
- Не начинай с пересказа слов клиента ("Понимаю что...", "Отлично что...")
- Каждый ответ уникальный

ПРИ ОТКАЗАХ:
- 1-й → уточни причину коротким вопросом
- 2-й → приведи мини-кейс (каждый раз новый)
- 3-й → предложи что-то лёгкое без обязательств
- 4+ → заверши по-человечески

СТАТУСЫ:
- talking — диалог, вопросы о цене/сроках/деталях (это НЕ warm)
- warm — клиент ЯВНО согласился: "давайте"/"хорошо"/"да", попросил созвониться, дал контакт. Вопрос о цене это НЕ warm
- rejected — 3+ явных отказа
- referral — перенаправил на другого человека с контактом

Формат — ТОЛЬКО JSON: {"reply": "текст", "status": "talking|warm|rejected|referral"}"""

REFERRAL_FIRST_MSG_PROMPT = """Напиши ПЕРВОЕ сообщение человеку, на которого тебя перенаправили.

ГЛАВНОЕ — ИСПОЛЬЗУЙ КОНТЕКСТ ПЕРЕПИСКИ:
- Внимательно прочитай историю переписки с тем, кто перенаправил
- Если в переписке упоминалось что этот человек уже что-то обсуждал / уже в курсе — учти это
- НЕ пиши как холодному лиду. Этот человек не случайный — на него указали конкретно
- Покажи что ты в курсе ситуации, а не начинаешь с нуля

КАК ПИСАТЬ:
- Коротко, 2-3 предложения максимум
- Упомяни кто направил — но нейтрально ("ваш коллега из ...", "в Шаурмэн посоветовали обратиться к вам"). НЕ пиши "ваша жена/муж" — ты не знаешь отношения людей
- Объясни зачем пишешь, опираясь на контекст из переписки
- НЕ дави на звонок — просто объясни контекст и задай вопрос
- Пиши как в мессенджере, без формальностей
- Поздоровайся через "Здравствуйте" (не "привет", не "здрасте") + имя если известно

ЗАПРЕТЫ:
- НЕ предлагай что-то новое если из переписки ясно что уже обсуждали — лучше спроси как прошло / чем закончилось
- НЕ используй фразы типа "заметил потенциал", "могу помочь" — это холодный подход
- НЕ угадывай семейные/личные связи между людьми

Формат — ТОЛЬКО JSON: {"reply": "текст сообщения"}"""

REFERRAL_EXTRACT_PROMPT = """Из переписки клиента извлеки контактные данные человека, на которого он перенаправляет.

Правила:
- Телефон: любой российский номер (+7/8...), вернуть в формате +7XXXXXXXXXX (только цифры, без пробелов)
- Имя: имя человека, на которого перенаправляют (не имя самого клиента, не должность)
- Если контакт передан визиткой [Контакт: имя, телефон] — извлеки оттуда
- Если телефон или имя не найдены — верни null для соответствующего поля

Формат — ТОЛЬКО JSON: {"phone": "+7XXXXXXXXXX", "name": "Имя"}"""

FOLLOWUP_SYSTEM_PROMPT = """Клиент не ответил. Напиши ОДНО короткое сообщение-крючок.

Правила:
- Привяжи к теме предыдущего диалога, не пиши абстрактно
- Если ранее обсуждали что-то конкретное, напомни об этом
- Если есть бесплатные опции в ИНФОРМАЦИИ ОБ УСЛУГАХ, предложи как лёгкий первый шаг
- Не повторяй предыдущие сообщения
- Пиши как в мессенджере, 1-2 предложения
- Не используй тире "—" и дефис "-"

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
                "max_tokens": 1500,
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
        service_info: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Генерирует ответ на сообщение лида.

        Args:
            conversation: История диалога [{role: "user"|"assistant", content: "..."}]
            custom_system_prompt: Кастомный промпт (если None — дефолтный)
            company_context: Контекст о компании для персонализации
            service_info: Информация об услугах и ценах

        Returns:
            {"reply": "текст", "status": "talking|warm|rejected"} или None
        """
        prompt = custom_system_prompt or SALES_SYSTEM_PROMPT
        if service_info:
            prompt += (
                "\n\nИНФОРМАЦИЯ ОБ УСЛУГАХ И ЦЕНАХ (справочная, используй ТОЛЬКО когда клиент сам спрашивает):\n"
                + service_info
            )
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

    async def generate_referral_first_message(
        self,
        referral_name: Optional[str],
        referrer_name: Optional[str],
        company_name: str,
        offer: str,
        referral_context: str,
    ) -> Optional[str]:
        """
        Генерирует первое сообщение для referral-контакта.

        Args:
            referral_name: Имя человека которому пишем
            referrer_name: Имя того кто перенаправил
            company_name: Название компании
            offer: Оффер кампании
            referral_context: Контекст из переписки с оригинальным лидом
        """
        context = (
            f"Человек которому пишешь: {referral_name or 'имя неизвестно'}\n"
            f"Кто перенаправил: {referrer_name or 'сотрудник'} из {company_name}\n"
            f"Оффер: {offer}\n"
            f"Контекст переписки:\n{referral_context}"
        )
        messages = [{"role": "user", "content": context}]
        result = await self._call_llm(REFERRAL_FIRST_MSG_PROMPT, messages)
        if result and result.get("reply"):
            return result["reply"]
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
