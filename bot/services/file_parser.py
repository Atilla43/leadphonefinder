"""Парсинг Excel и CSV файлов."""

import pandas as pd
from io import BytesIO
from typing import Tuple

from bot.models.company import Company, EnrichmentStatus
from bot.services.inn_validator import validate_inn, normalize_inn


class FileParseError(Exception):
    """Ошибка парсинга файла."""

    pass


def parse_file(file_bytes: bytes, filename: str) -> list[Company]:
    """
    Парсит Excel или CSV файл в список компаний.

    Args:
        file_bytes: Содержимое файла в байтах
        filename: Имя файла (для определения формата)

    Returns:
        Список объектов Company

    Raises:
        FileParseError: При ошибке парсинга
    """
    try:
        if filename.lower().endswith(".xlsx") or filename.lower().endswith(".xls"):
            df = pd.read_excel(BytesIO(file_bytes))
        elif filename.lower().endswith(".csv"):
            # Пробуем разные кодировки
            for encoding in ["utf-8", "cp1251", "utf-8-sig"]:
                try:
                    df = pd.read_csv(BytesIO(file_bytes), encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise FileParseError("Не удалось определить кодировку CSV файла")
        else:
            raise FileParseError(
                "Неподдерживаемый формат файла. Используйте .xlsx или .csv"
            )

    except Exception as e:
        if isinstance(e, FileParseError):
            raise
        raise FileParseError(f"Ошибка чтения файла: {str(e)}")

    # Нормализация названий колонок
    df.columns = df.columns.str.strip().str.lower()

    # Поиск колонки ИНН
    inn_col = _find_column(df.columns, ["инн", "inn", "ИНН"])
    if not inn_col:
        raise FileParseError(
            "Не найдена колонка 'ИНН'. Убедитесь, что файл содержит колонку с ИНН."
        )

    # Поиск колонки Название
    name_col = _find_column(
        df.columns, ["название", "name", "наименование", "компания", "организация"]
    )
    if not name_col:
        raise FileParseError(
            "Не найдена колонка 'Название'. Убедитесь, что файл содержит колонку с названием компании."
        )

    companies = []
    for idx, row in df.iterrows():
        # Получаем и нормализуем ИНН
        raw_inn = str(row[inn_col]).strip() if pd.notna(row[inn_col]) else ""
        inn = normalize_inn(raw_inn)

        # Получаем название
        name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""

        # Пропускаем пустые строки
        if not inn and not name:
            continue

        company = Company(inn=inn, name=name)

        # Валидация ИНН
        if not inn or not validate_inn(inn):
            company.status = EnrichmentStatus.INVALID_INN

        companies.append(company)

    if not companies:
        raise FileParseError("Файл не содержит данных для обработки")

    return companies


def _find_column(columns: pd.Index, variants: list[str]) -> str | None:
    """Ищет колонку по списку вариантов названий."""
    columns_lower = [c.lower() for c in columns]
    for variant in variants:
        variant_lower = variant.lower()
        # Точное совпадение
        if variant_lower in columns_lower:
            idx = columns_lower.index(variant_lower)
            return columns[idx]
        # Частичное совпадение
        for i, col in enumerate(columns_lower):
            if variant_lower in col:
                return columns[i]
    return None


def get_file_stats(companies: list[Company]) -> dict:
    """
    Получает статистику по распаршенному файлу.

    Args:
        companies: Список компаний

    Returns:
        Словарь со статистикой
    """
    total = len(companies)
    valid = sum(1 for c in companies if c.status != EnrichmentStatus.INVALID_INN)
    invalid = sum(1 for c in companies if c.status == EnrichmentStatus.INVALID_INN)

    # Подсчёт дубликатов по ИНН
    inns = [c.inn for c in companies if c.inn]
    duplicates = len(inns) - len(set(inns))

    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "duplicates": duplicates,
    }
