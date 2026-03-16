"""Парсинг Excel и CSV файлов."""

import re

import pandas as pd
from io import BytesIO
from typing import Tuple

from bot.models.company import Company, EnrichmentStatus
from bot.models.outreach import OutreachRecipient
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


def _safe_str(row, col: str | None) -> str | None:
    """Безопасно извлекает строку из ячейки DataFrame."""
    if not col or pd.isna(row[col]):
        return None
    val = str(row[col]).strip()
    return val if val else None


def _normalize_phone(phone: str) -> str:
    """Нормализует телефон в формат +7XXXXXXXXXX."""
    digits = re.sub(r"[^\d]", "", phone)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    if not digits.startswith("7"):
        return ""
    if len(digits) != 11:
        return ""
    return "+" + digits


def detect_outreach_file(file_bytes: bytes, filename: str) -> bool:
    """
    Определяет, содержит ли файл колонку с телефонами (для outreach).

    Returns:
        True если файл содержит колонку телефонов
    """
    try:
        if filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(BytesIO(file_bytes))
        elif filename.lower().endswith(".csv"):
            for encoding in ["utf-8", "cp1251", "utf-8-sig"]:
                try:
                    df = pd.read_csv(BytesIO(file_bytes), encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return False
        else:
            return False

        df.columns = df.columns.str.strip().str.lower()
        phone_col = _find_column(df.columns, ["телефон", "phone", "номер", "тел"])
        inn_col = _find_column(df.columns, ["инн", "inn", "ИНН"])

        # Считаем outreach-файлом если есть телефоны и нет ИНН
        return phone_col is not None and inn_col is None
    except Exception:
        return False


def parse_outreach_file(file_bytes: bytes, filename: str) -> list[OutreachRecipient]:
    """
    Парсит файл с телефонами для outreach.

    Ожидаемые колонки: Телефон, Название компании, Имя контакта (опционально)

    Raises:
        FileParseError: При ошибке парсинга
    """
    try:
        if filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(BytesIO(file_bytes))
        elif filename.lower().endswith(".csv"):
            for encoding in ["utf-8", "cp1251", "utf-8-sig"]:
                try:
                    df = pd.read_csv(BytesIO(file_bytes), encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise FileParseError("Не удалось определить кодировку CSV файла")
        else:
            raise FileParseError("Неподдерживаемый формат файла")
    except Exception as e:
        if isinstance(e, FileParseError):
            raise
        raise FileParseError(f"Ошибка чтения файла: {str(e)}")

    df.columns = df.columns.str.strip().str.lower()

    # Ищем колонку телефона
    phone_col = _find_column(df.columns, ["телефон", "phone", "номер", "тел"])
    if not phone_col:
        raise FileParseError(
            "Не найдена колонка 'Телефон'. Файл должен содержать колонку с телефонами."
        )

    # Ищем колонку названия компании
    name_col = _find_column(
        df.columns, ["название", "компания", "name", "company", "наименование", "организация"]
    )

    # Ищем колонку имени контакта
    contact_col = _find_column(
        df.columns, ["контакт", "имя", "contact", "фио", "лицо"]
    )

    # Дополнительные колонки для контекста AI продажника
    category_col = _find_column(df.columns, ["категория", "category"])
    rating_col = _find_column(df.columns, ["рейтинг", "rating"])
    reviews_col = _find_column(df.columns, ["отзывов", "отзывы", "reviews"])
    website_col = _find_column(df.columns, ["сайт", "website", "url"])
    hours_col = _find_column(df.columns, ["время работы", "часы", "working_hours"])
    address_col = _find_column(df.columns, ["адрес", "address"])
    director_col = _find_column(df.columns, ["директор", "director", "руководитель"])

    recipients = []
    for _, row in df.iterrows():
        raw_phone = str(row[phone_col]).strip() if pd.notna(row[phone_col]) else ""
        # Берём первый телефон, если несколько через запятую
        if "," in raw_phone:
            raw_phone = raw_phone.split(",")[0].strip()
        phone = _normalize_phone(raw_phone)
        if not phone:
            continue

        company_name = ""
        if name_col and pd.notna(row[name_col]):
            company_name = str(row[name_col]).strip()

        contact_name = None
        if contact_col and pd.notna(row[contact_col]):
            contact_name = str(row[contact_col]).strip() or None

        # Извлекаем контекст компании
        category = _safe_str(row, category_col)
        website = _safe_str(row, website_col)
        working_hours = _safe_str(row, hours_col)
        address = _safe_str(row, address_col)
        director_name = _safe_str(row, director_col)

        rating = None
        if rating_col and pd.notna(row[rating_col]):
            try:
                rating = float(row[rating_col])
            except (ValueError, TypeError):
                pass

        reviews_count = None
        if reviews_col and pd.notna(row[reviews_col]):
            try:
                reviews_count = int(float(row[reviews_col]))
            except (ValueError, TypeError):
                pass

        recipients.append(OutreachRecipient(
            phone=phone,
            company_name=company_name or "Компания",
            contact_name=contact_name,
            category=category,
            rating=rating,
            reviews_count=reviews_count,
            website=website,
            working_hours=working_hours,
            address=address,
            director_name=director_name,
        ))

    if not recipients:
        raise FileParseError("Файл не содержит валидных телефонов для рассылки")

    return recipients


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
