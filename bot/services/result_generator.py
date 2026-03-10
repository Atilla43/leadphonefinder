"""Генерация результирующих файлов."""

import pandas as pd
from io import BytesIO
from datetime import datetime

from bot.models.company import Company


def generate_excel(companies: list[Company], filename_prefix: str = "result") -> tuple[bytes, str]:
    """
    Генерирует Excel файл с результатами.

    Args:
        companies: Список компаний с результатами
        filename_prefix: Префикс имени файла

    Returns:
        Tuple (содержимое файла в байтах, имя файла)
    """
    data = [c.to_dict() for c in companies]
    df = pd.DataFrame(data)

    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"{filename_prefix}_{timestamp}.xlsx"

    return buffer.getvalue(), filename


def generate_csv(companies: list[Company], filename_prefix: str = "result") -> tuple[bytes, str]:
    """
    Генерирует CSV файл с результатами.

    Args:
        companies: Список компаний с результатами
        filename_prefix: Префикс имени файла

    Returns:
        Tuple (содержимое файла в байтах, имя файла)
    """
    data = [c.to_dict() for c in companies]
    df = pd.DataFrame(data)

    # UTF-8 with BOM для корректного открытия в Excel
    content = df.to_csv(index=False).encode("utf-8-sig")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"{filename_prefix}_{timestamp}.csv"

    return content, filename


def generate_template_excel() -> tuple[bytes, str]:
    """
    Генерирует шаблон Excel файла.

    Returns:
        Tuple (содержимое файла в байтах, имя файла)
    """
    data = [
        {"ИНН": "7707083893", "Название": "ПАО Сбербанк"},
        {"ИНН": "7728168971", "Название": "ООО Яндекс"},
        {"ИНН": "7702070139", "Название": "ПАО МТС"},
    ]
    df = pd.DataFrame(data)

    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    return buffer.getvalue(), "template.xlsx"


def generate_outreach_template() -> tuple[bytes, str]:
    """
    Генерирует шаблон Excel для AI-Продажника.

    Returns:
        Tuple (содержимое файла в байтах, имя файла)
    """
    data = [
        {"Телефон": "+79001234567", "Компания": "ООО Рога и Копыта", "Контакт": "Иванов Иван"},
        {"Телефон": "+79009876543", "Компания": "ИП Петров", "Контакт": "Петров Пётр"},
        {"Телефон": "+79005556677", "Компания": "ООО Ромашка", "Контакт": ""},
    ]
    df = pd.DataFrame(data)

    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    return buffer.getvalue(), "outreach_template.xlsx"


def generate_template_csv() -> tuple[bytes, str]:
    """
    Генерирует шаблон CSV файла.

    Returns:
        Tuple (содержимое файла в байтах, имя файла)
    """
    data = [
        {"ИНН": "7707083893", "Название": "ПАО Сбербанк"},
        {"ИНН": "7728168971", "Название": "ООО Яндекс"},
        {"ИНН": "7702070139", "Название": "ПАО МТС"},
    ]
    df = pd.DataFrame(data)

    content = df.to_csv(index=False).encode("utf-8-sig")

    return content, "template.csv"
