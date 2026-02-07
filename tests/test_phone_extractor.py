"""Тесты извлечения телефонов."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.services.phone_extractor import extract_phones, format_phone, mask_phone


class TestExtractPhones:
    """Тесты функции extract_phones."""

    # Стандартные форматы
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("+7 (916) 123-45-67", ["+79161234567"]),
            ("+7(916)123-45-67", ["+79161234567"]),
            ("+7 916 123 45 67", ["+79161234567"]),
            ("+79161234567", ["+79161234567"]),
            ("8 (916) 123-45-67", ["+79161234567"]),
            ("8-916-123-45-67", ["+79161234567"]),
            ("89161234567", ["+79161234567"]),
        ],
    )
    def test_single_phone_formats(self, text: str, expected: list):
        """Извлечение телефона в разных форматах."""
        assert extract_phones(text) == expected

    def test_multiple_phones(self):
        """Несколько телефонов в тексте."""
        text = """
        Контакты:
        Основной: +7 (916) 111-22-33
        Дополнительный: 8-903-444-55-66
        Факс: +7 495 777-88-99
        """
        result = extract_phones(text)
        assert "+79161112233" in result
        assert "+79034445566" in result
        assert "+74957778899" in result
        assert len(result) == 3

    def test_no_phones(self):
        """Текст без телефонов."""
        text = "Компания ООО Тест, ИНН 7707083893, адрес: Москва"
        result = extract_phones(text)
        assert result == []

    def test_empty_input(self):
        """Пустой ввод."""
        assert extract_phones("") == []
        assert extract_phones(None) == []

    def test_deduplication(self):
        """Удаление дубликатов."""
        text = "+79161234567 +79161234567 89161234567"
        result = extract_phones(text)
        assert len(result) == 1
        assert result[0] == "+79161234567"

    def test_real_sherlock_response(self):
        """Парсинг реального ответа."""
        text = """
        🏢 ООО "АЛЬФА ТЕХНОЛОГИИ"
        ИНН: 7707083893
        Директор: Иванов Иван Иванович

        📱 Телефоны:
        +7 (916) 123-45-67 (мобильный)
        +7 (495) 999-88-77 (офис)

        📧 Email: info@alpha.ru
        """
        result = extract_phones(text)
        assert "+79161234567" in result
        assert "+74959998877" in result
        assert len(result) == 2


class TestFormatPhone:
    """Тесты функции format_phone."""

    @pytest.mark.parametrize(
        "phone,expected",
        [
            ("+79161234567", "+7 (916) 123-45-67"),
            ("+74951234567", "+7 (495) 123-45-67"),
            ("invalid", "invalid"),
            ("", ""),
        ],
    )
    def test_format_phone(self, phone: str, expected: str):
        """Форматирование телефона."""
        assert format_phone(phone) == expected


class TestMaskPhone:
    """Тесты функции mask_phone."""

    @pytest.mark.parametrize(
        "phone,expected",
        [
            ("+79161234567", "+7 916 ***-**-67"),
            ("+74951234567", "+7 495 ***-**-67"),
            ("invalid", "invalid"),
            ("", ""),
        ],
    )
    def test_mask_phone(self, phone: str, expected: str):
        """Маскирование телефона."""
        assert mask_phone(phone) == expected
