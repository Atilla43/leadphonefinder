"""Тесты валидации ИНН."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.services.inn_validator import validate_inn, normalize_inn


class TestValidateINN:
    """Тесты функции validate_inn."""

    # Валидные ИНН юридических лиц (10 цифр)
    @pytest.mark.parametrize(
        "inn",
        [
            "7707083893",  # Сбербанк
            "7728168971",  # Яндекс
            "7702070139",  # МТС
            "7736050003",  # Газпром
            "7707049388",  # ВТБ
            "7703399906",  # Тинькофф
        ],
    )
    def test_valid_inn_10_digits(self, inn: str):
        """Валидные ИНН юридических лиц."""
        assert validate_inn(inn) is True

    # Валидные ИНН физических лиц / ИП (12 цифр)
    @pytest.mark.parametrize(
        "inn",
        [
            "500100732259",
            "772770015580",
        ],
    )
    def test_valid_inn_12_digits(self, inn: str):
        """Валидные ИНН физических лиц / ИП."""
        assert validate_inn(inn) is True

    # Невалидные ИНН
    @pytest.mark.parametrize(
        "inn,description",
        [
            ("1234567890", "Неверная контрольная сумма"),
            ("0000000000", "Все нули"),
            ("123456789", "9 цифр"),
            ("12345678901", "11 цифр"),
            ("1234567890123", "13 цифр"),
            ("12345abcde", "Содержит буквы"),
            ("", "Пустая строка"),
            ("   ", "Только пробелы"),
            ("77-07-08-38-93", "С дефисами"),
            ("7707 0838 93", "С пробелами"),
        ],
    )
    def test_invalid_inn(self, inn: str, description: str):
        """Невалидные ИНН: {description}."""
        assert validate_inn(inn) is False

    def test_none_input(self):
        """None на входе."""
        assert validate_inn(None) is False

    def test_integer_input(self):
        """Число вместо строки."""
        # Функция ожидает строку, но не должна падать
        assert validate_inn(7707083893) is False


class TestNormalizeINN:
    """Тесты функции normalize_inn."""

    @pytest.mark.parametrize(
        "input_inn,expected",
        [
            ("7707083893", "7707083893"),
            ("  7707083893  ", "7707083893"),
            ("77-07-08-38-93", "7707083893"),
            ("7707 0838 93", "7707083893"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_normalize_inn(self, input_inn, expected):
        """Нормализация ИНН."""
        assert normalize_inn(input_inn) == expected
