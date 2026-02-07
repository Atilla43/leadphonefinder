"""Тесты парсинга файлов."""

import pytest
import pandas as pd
from io import BytesIO
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.services.file_parser import parse_file, get_file_stats, FileParseError
from bot.models.company import EnrichmentStatus


def create_excel(data: list[dict]) -> bytes:
    """Создаёт Excel файл в памяти."""
    df = pd.DataFrame(data)
    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


def create_csv(data: list[dict], encoding: str = "utf-8") -> bytes:
    """Создаёт CSV файл в памяти."""
    df = pd.DataFrame(data)
    return df.to_csv(index=False).encode(encoding)


class TestParseFile:
    """Тесты функции parse_file."""

    def test_parse_excel_valid(self):
        """Парсинг валидного Excel."""
        data = [
            {"ИНН": "7707083893", "Название": "Сбербанк"},
            {"ИНН": "7728168971", "Название": "Яндекс"},
        ]
        file_bytes = create_excel(data)

        result = parse_file(file_bytes, "test.xlsx")

        assert len(result) == 2
        assert result[0].inn == "7707083893"
        assert result[0].name == "Сбербанк"
        assert result[1].inn == "7728168971"
        assert result[1].name == "Яндекс"

    def test_parse_csv_valid(self):
        """Парсинг валидного CSV."""
        data = [
            {"ИНН": "7707083893", "Название": "Сбербанк"},
        ]
        file_bytes = create_csv(data)

        result = parse_file(file_bytes, "test.csv")

        assert len(result) == 1
        assert result[0].inn == "7707083893"

    def test_invalid_inn_marked(self):
        """Невалидные ИНН помечаются."""
        data = [
            {"ИНН": "7707083893", "Название": "Валидный"},
            {"ИНН": "invalid123", "Название": "Невалидный"},
            {"ИНН": "1234567890", "Название": "Неверная контрольная сумма"},
        ]
        file_bytes = create_excel(data)

        result = parse_file(file_bytes, "test.xlsx")

        assert result[0].status == EnrichmentStatus.PENDING
        assert result[1].status == EnrichmentStatus.INVALID_INN
        assert result[2].status == EnrichmentStatus.INVALID_INN

    def test_missing_inn_column(self):
        """Ошибка при отсутствии колонки ИНН."""
        data = [{"Колонка1": "123", "Название": "Тест"}]
        file_bytes = create_excel(data)

        with pytest.raises(FileParseError) as exc_info:
            parse_file(file_bytes, "test.xlsx")
        assert "ИНН" in str(exc_info.value)

    def test_missing_name_column(self):
        """Ошибка при отсутствии колонки Название."""
        data = [{"ИНН": "7707083893", "Колонка2": "Тест"}]
        file_bytes = create_excel(data)

        with pytest.raises(FileParseError) as exc_info:
            parse_file(file_bytes, "test.xlsx")
        assert "Название" in str(exc_info.value)

    def test_unsupported_format(self):
        """Ошибка при неподдерживаемом формате."""
        with pytest.raises(FileParseError) as exc_info:
            parse_file(b"data", "test.pdf")
        assert "формат" in str(exc_info.value).lower()

    def test_alternative_column_names(self):
        """Альтернативные названия колонок (английские)."""
        data = [{"inn": "7707083893", "name": "Test Company"}]
        file_bytes = create_excel(data)

        result = parse_file(file_bytes, "test.xlsx")
        assert result[0].inn == "7707083893"
        assert result[0].name == "Test Company"

    def test_whitespace_handling(self):
        """Обработка пробелов в данных."""
        data = [{"ИНН": "  7707083893  ", "Название": "  Сбербанк  "}]
        file_bytes = create_excel(data)

        result = parse_file(file_bytes, "test.xlsx")
        assert result[0].inn == "7707083893"
        assert result[0].name == "Сбербанк"

    def test_empty_file(self):
        """Пустой файл."""
        data = []
        file_bytes = create_excel(data)

        with pytest.raises(FileParseError):
            parse_file(file_bytes, "test.xlsx")


class TestGetFileStats:
    """Тесты функции get_file_stats."""

    def test_stats_calculation(self):
        """Расчёт статистики."""
        data = [
            {"ИНН": "7707083893", "Название": "Валидный1"},
            {"ИНН": "7728168971", "Название": "Валидный2"},
            {"ИНН": "invalid", "Название": "Невалидный"},
            {"ИНН": "7707083893", "Название": "Дубликат"},
        ]
        file_bytes = create_excel(data)
        companies = parse_file(file_bytes, "test.xlsx")

        stats = get_file_stats(companies)

        assert stats["total"] == 4
        assert stats["valid"] == 3  # 2 валидных + 1 дубликат (валидный ИНН)
        assert stats["invalid"] == 1
        assert stats["duplicates"] == 1
