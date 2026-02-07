"""Дедупликация результатов скраппинга."""

import logging
import re
from typing import Optional

from bot.services.scrapper.models import ScrapedCompany, ScrapperSource

logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """
    Нормализует название компании для сравнения.

    - Приводит к нижнему регистру
    - Убирает кавычки и спецсимволы
    - Убирает юридическую форму (ООО, ИП и т.д.)
    """
    if not name:
        return ""

    result = name.lower().strip()

    # Убираем кавычки
    result = re.sub(r'[«»"\'\"\"\']', '', result)

    # Убираем юридическую форму
    legal_forms = [
        r'\bооо\b', r'\bоао\b', r'\bзао\b', r'\bпао\b',
        r'\bип\b', r'\bчп\b', r'\bнко\b', r'\bано\b',
        r'\bгуп\b', r'\bмуп\b', r'\bфгуп\b',
        r'\bllc\b', r'\binc\b', r'\bltd\b', r'\bcorp\b',
    ]
    for form in legal_forms:
        result = re.sub(form, '', result)

    # Убираем лишние пробелы
    result = re.sub(r'\s+', ' ', result).strip()

    return result


def normalize_address(address: str) -> str:
    """
    Нормализует адрес для сравнения.

    - Приводит к нижнему регистру
    - Убирает индекс
    - Сокращает типы улиц
    """
    if not address:
        return ""

    result = address.lower().strip()

    # Убираем индекс (6 цифр)
    result = re.sub(r'\d{6}', '', result)

    # Стандартизируем типы улиц
    replacements = {
        r'\bулица\b': 'ул',
        r'\bпроспект\b': 'пр',
        r'\bпереулок\b': 'пер',
        r'\bбульвар\b': 'бул',
        r'\bшоссе\b': 'ш',
        r'\bнабережная\b': 'наб',
        r'\bплощадь\b': 'пл',
        r'\bкорпус\b': 'к',
        r'\bстроение\b': 'стр',
        r'\bэтаж\b': 'эт',
        r'\bофис\b': 'оф',
        r'\bпомещение\b': 'пом',
    }

    for pattern, replacement in replacements.items():
        result = re.sub(pattern, replacement, result)

    # Убираем лишние пробелы и запятые
    result = re.sub(r'[,\s]+', ' ', result).strip()

    return result


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """Нормализует телефон к формату +7XXXXXXXXXX."""
    if not phone:
        return None

    # Оставляем только цифры
    digits = re.sub(r'\D', '', phone)

    if len(digits) == 11:
        if digits.startswith('8'):
            return '+7' + digits[1:]
        elif digits.startswith('7'):
            return '+' + digits

    if len(digits) == 10:
        return '+7' + digits

    return phone  # Возвращаем как есть


def fuzzy_match(s1: str, s2: str, threshold: float = 0.85) -> bool:
    """
    Нечёткое сравнение строк (простой алгоритм).

    Args:
        s1: Первая строка
        s2: Вторая строка
        threshold: Порог схожести (0-1)

    Returns:
        True если строки похожи
    """
    if not s1 or not s2:
        return False

    # Точное совпадение
    if s1 == s2:
        return True

    # Одна строка содержит другую
    if s1 in s2 or s2 in s1:
        return True

    # Расстояние Левенштейна (упрощённое)
    # Для длинных строк используем соотношение
    len1, len2 = len(s1), len(s2)
    max_len = max(len1, len2)

    if max_len == 0:
        return True

    # Считаем общие символы
    common = sum(1 for c in s1 if c in s2)
    similarity = common / max_len

    return similarity >= threshold


class Deduplicator:
    """Дедупликатор результатов скраппинга."""

    def __init__(
        self,
        name_threshold: float = 0.85,
        address_threshold: float = 0.80,
        prefer_source: Optional[ScrapperSource] = None,
    ) -> None:
        """
        Инициализация дедупликатора.

        Args:
            name_threshold: Порог схожести названий
            address_threshold: Порог схожести адресов
            prefer_source: Предпочтительный источник при дубликатах
        """
        self.name_threshold = name_threshold
        self.address_threshold = address_threshold
        self.prefer_source = prefer_source

    def deduplicate(
        self,
        companies: list[ScrapedCompany]
    ) -> tuple[list[ScrapedCompany], int]:
        """
        Удаляет дубликаты из списка компаний.

        Args:
            companies: Список компаний

        Returns:
            Кортеж (уникальные компании, количество удалённых дубликатов)
        """
        if not companies:
            return [], 0

        unique: list[ScrapedCompany] = []
        duplicates_count = 0

        for company in companies:
            is_duplicate = False

            for existing in unique:
                if self._is_duplicate(company, existing):
                    is_duplicate = True
                    duplicates_count += 1

                    # Объединяем данные
                    self._merge_companies(existing, company)
                    break

            if not is_duplicate:
                unique.append(company)

        logger.info(
            f"Deduplicated: {len(companies)} -> {len(unique)} "
            f"(removed {duplicates_count} duplicates)"
        )

        return unique, duplicates_count

    def _is_duplicate(
        self,
        company1: ScrapedCompany,
        company2: ScrapedCompany
    ) -> bool:
        """
        Проверяет являются ли две компании дубликатами.

        Критерии дубликата:
        1. Одинаковый ИНН (если есть)
        2. Похожие название И адрес
        3. Одинаковый телефон (если есть)
        """
        # По ИНН (точное совпадение)
        if company1.inn and company2.inn:
            if company1.inn == company2.inn:
                return True

        # По телефону (если оба есть)
        phone1 = normalize_phone(company1.phone)
        phone2 = normalize_phone(company2.phone)
        if phone1 and phone2 and phone1 == phone2:
            return True

        # По названию и адресу
        name1 = normalize_name(company1.name)
        name2 = normalize_name(company2.name)

        if not fuzzy_match(name1, name2, self.name_threshold):
            return False

        # Названия похожи, проверяем адрес
        addr1 = normalize_address(company1.address)
        addr2 = normalize_address(company2.address)

        # Если оба адреса пустые - считаем дубликатом по названию
        if not addr1 and not addr2:
            return True

        # Если один пустой - не дубликат (может быть филиал)
        if not addr1 or not addr2:
            return False

        return fuzzy_match(addr1, addr2, self.address_threshold)

    def _merge_companies(
        self,
        target: ScrapedCompany,
        source: ScrapedCompany
    ) -> None:
        """
        Объединяет данные двух компаний в target.

        Заполняет пустые поля данными из source.
        """
        # Телефон
        if not target.phone and source.phone:
            target.phone = source.phone

        # ИНН
        if not target.inn and source.inn:
            target.inn = source.inn

        # Сайт
        if not target.website and source.website:
            target.website = source.website

        # Рейтинг (берём выше)
        if source.rating:
            if not target.rating or source.rating > target.rating:
                target.rating = source.rating

        # Количество отзывов (берём больше)
        if source.reviews_count:
            if not target.reviews_count or source.reviews_count > target.reviews_count:
                target.reviews_count = source.reviews_count

        # Категория
        if not target.category and source.category:
            target.category = source.category

        # Координаты
        if not target.latitude and source.latitude:
            target.latitude = source.latitude
            target.longitude = source.longitude

        # Часы работы
        if not target.working_hours and source.working_hours:
            target.working_hours = source.working_hours
