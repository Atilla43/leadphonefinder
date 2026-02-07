"""Извлечение телефонных номеров из текста."""

import re
from typing import Optional


def extract_phones(text: Optional[str]) -> list[str]:
    """
    Извлекает российские телефоны из текста.

    Поддерживаемые форматы:
    - +7 (XXX) XXX-XX-XX
    - +7XXXXXXXXXX
    - 8 (XXX) XXX-XX-XX
    - 8XXXXXXXXXX
    - 7XXXXXXXXXX (без +)
    - (XXX) XXX-XX-XX (без кода страны)

    Args:
        text: Текст для поиска телефонов

    Returns:
        Список телефонов в формате +7XXXXXXXXXX
    """
    if not text:
        return []

    # Паттерны для разных форматов номеров
    patterns = [
        # +7 с разными разделителями
        r"\+7\s*[\(\-]?\s*(\d{3})\s*[\)\-]?\s*(\d{3})\s*[\-\s]?(\d{2})\s*[\-\s]?(\d{2})",
        # 8 с разными разделителями
        r"(?<!\d)8\s*[\(\-]?\s*(\d{3})\s*[\)\-]?\s*(\d{3})\s*[\-\s]?(\d{2})\s*[\-\s]?(\d{2})",
        # Без пробелов: +79161234567 или 89161234567
        r"(?:\+7|8)(\d{10})",
        # Без кода страны: (916) 123-45-67 или 916 123 45 67
        r"(?<!\d)\(?(\d{3})\)?\s*[\-\s]?(\d{3})\s*[\-\s]?(\d{2})\s*[\-\s]?(\d{2})(?!\d)",
    ]

    found_phones = []

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                # Собираем цифры из групп
                digits = "".join(match)
            else:
                digits = match

            # Убираем все нецифровые символы
            digits = re.sub(r"\D", "", digits)

            if len(digits) == 10:
                # Добавляем код страны
                digits = "7" + digits
            elif len(digits) == 11 and digits[0] == "8":
                # Заменяем 8 на 7
                digits = "7" + digits[1:]

            if len(digits) == 11 and digits[0] == "7":
                found_phones.append("+7" + digits[1:])

    # Убираем дубликаты, сохраняя порядок
    seen = set()
    unique_phones = []
    for phone in found_phones:
        if phone not in seen:
            seen.add(phone)
            unique_phones.append(phone)

    return unique_phones


def format_phone(phone: str) -> str:
    """
    Форматирует телефон в читаемый вид.

    Args:
        phone: Телефон в формате +7XXXXXXXXXX

    Returns:
        Телефон в формате +7 (XXX) XXX-XX-XX
    """
    if not phone or len(phone) != 12:
        return phone

    digits = phone.replace("+", "")
    if len(digits) != 11:
        return phone

    return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"


def mask_phone(phone: str) -> str:
    """
    Маскирует часть телефона для отображения.

    Args:
        phone: Телефон в формате +7XXXXXXXXXX

    Returns:
        Телефон с маской: +7 916 ***-**-67
    """
    if not phone or len(phone) != 12:
        return phone

    digits = phone.replace("+", "")
    if len(digits) != 11:
        return phone

    return f"+7 {digits[1:4]} ***-**-{digits[9:11]}"
