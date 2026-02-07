"""Парсер поисковых запросов пользователя с исправлением опечаток."""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Вычисляет расстояние Левенштейна между двумя строками.
    Чем меньше значение, тем более похожи строки.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Вставка, удаление, замена
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def fuzzy_find_best_match(
    query: str,
    candidates: list[str],
    max_distance: int = 2,
) -> Optional[str]:
    """
    Находит лучшее совпадение с учётом опечаток.

    Args:
        query: Искомая строка (возможно с опечаткой)
        candidates: Список кандидатов
        max_distance: Максимальное расстояние Левенштейна

    Returns:
        Лучший кандидат или None
    """
    if not query or not candidates:
        return None

    query_lower = query.lower().strip()

    # Сначала точное совпадение
    for candidate in candidates:
        if candidate.lower() == query_lower:
            return candidate

    # Затем fuzzy matching
    best_match = None
    best_distance = max_distance + 1

    for candidate in candidates:
        candidate_lower = candidate.lower()
        distance = levenshtein_distance(query_lower, candidate_lower)

        # Учитываем длину слова для порога
        # Для коротких слов (3-4 буквы) допускаем 1 ошибку
        # Для длинных (7+) допускаем 2-3 ошибки
        adjusted_max = min(max_distance, max(1, len(candidate_lower) // 3))

        if distance <= adjusted_max and distance < best_distance:
            best_distance = distance
            best_match = candidate

    return best_match

# Популярные города России с координатами (центр и bbox)
CITIES = {
    # Москва и область
    "москва": {"lat": 55.7558, "lon": 37.6173, "bbox": "37.2,55.5,37.9,55.95"},
    "мск": {"lat": 55.7558, "lon": 37.6173, "bbox": "37.2,55.5,37.9,55.95"},

    # Санкт-Петербург
    "санкт-петербург": {"lat": 59.9343, "lon": 30.3351, "bbox": "29.8,59.7,30.8,60.15"},
    "спб": {"lat": 59.9343, "lon": 30.3351, "bbox": "29.8,59.7,30.8,60.15"},
    "питер": {"lat": 59.9343, "lon": 30.3351, "bbox": "29.8,59.7,30.8,60.15"},

    # Юг России
    "сочи": {"lat": 43.6028, "lon": 39.7342, "bbox": "39.5,43.4,40.0,43.8"},
    "краснодар": {"lat": 45.0355, "lon": 38.9753, "bbox": "38.7,44.85,39.2,45.2"},
    "ростов-на-дону": {"lat": 47.2357, "lon": 39.7015, "bbox": "39.4,47.05,40.0,47.4"},
    "ростов": {"lat": 47.2357, "lon": 39.7015, "bbox": "39.4,47.05,40.0,47.4"},

    # Поволжье
    "казань": {"lat": 55.7887, "lon": 49.1221, "bbox": "48.8,55.6,49.4,56.0"},
    "нижний новгород": {"lat": 56.2965, "lon": 43.9361, "bbox": "43.6,56.15,44.2,56.45"},
    "самара": {"lat": 53.1959, "lon": 50.1002, "bbox": "49.8,53.0,50.4,53.35"},
    "волгоград": {"lat": 48.7080, "lon": 44.5133, "bbox": "44.2,48.5,44.8,48.9"},

    # Урал
    "екатеринбург": {"lat": 56.8389, "lon": 60.6057, "bbox": "60.3,56.65,60.9,57.0"},
    "челябинск": {"lat": 55.1644, "lon": 61.4368, "bbox": "61.1,55.0,61.7,55.35"},
    "пермь": {"lat": 58.0105, "lon": 56.2502, "bbox": "55.9,57.85,56.5,58.15"},
    "уфа": {"lat": 54.7388, "lon": 55.9721, "bbox": "55.7,54.55,56.2,54.9"},

    # Сибирь
    "новосибирск": {"lat": 55.0084, "lon": 82.9357, "bbox": "82.6,54.8,83.2,55.2"},
    "красноярск": {"lat": 56.0153, "lon": 92.8932, "bbox": "92.5,55.85,93.2,56.15"},
    "омск": {"lat": 54.9914, "lon": 73.3645, "bbox": "73.0,54.8,73.7,55.15"},
    "томск": {"lat": 56.4977, "lon": 84.9744, "bbox": "84.7,56.35,85.2,56.65"},

    # Дальний Восток
    "владивосток": {"lat": 43.1332, "lon": 131.9113, "bbox": "131.6,42.95,132.2,43.3"},
    "хабаровск": {"lat": 48.4827, "lon": 135.0838, "bbox": "134.8,48.3,135.4,48.65"},

    # Другие крупные города
    "воронеж": {"lat": 51.6720, "lon": 39.1843, "bbox": "38.9,51.5,39.45,51.85"},
    "саратов": {"lat": 51.5406, "lon": 46.0086, "bbox": "45.7,51.35,46.3,51.7"},
    "тюмень": {"lat": 57.1522, "lon": 65.5272, "bbox": "65.2,57.0,65.8,57.3"},
    "ярославль": {"lat": 57.6261, "lon": 39.8845, "bbox": "39.6,57.45,40.1,57.75"},
    "калининград": {"lat": 54.7104, "lon": 20.4522, "bbox": "20.2,54.55,20.7,54.85"},
}

# Синонимы категорий
CATEGORY_SYNONYMS = {
    # Рестораны и еда
    "рестораны": ["ресторан", "ресторана", "ресторанов", "кафе", "общепит"],
    "кафе": ["кафешки", "кофейни", "кофейня"],
    "бары": ["бар", "паб", "пабы"],
    "пиццерии": ["пиццерия", "пицца"],
    "суши": ["суши-бар", "японская кухня", "роллы"],
    "фастфуд": ["fast food", "быстрое питание"],

    # Услуги
    "автосервисы": ["автосервис", "сто", "автомастерская", "ремонт авто"],
    "салоны красоты": ["салон красоты", "парикмахерская", "барбершоп", "маникюр"],
    "фитнес": ["фитнес-клуб", "спортзал", "тренажерный зал", "gym"],
    "стоматологии": ["стоматология", "зубной", "дантист", "dental"],
    "клиники": ["клиника", "медцентр", "больница"],

    # Торговля
    "магазины": ["магазин", "shop", "маркет"],
    "супермаркеты": ["супермаркет", "гипермаркет", "продукты"],
    "аптеки": ["аптека", "pharmacy"],

    # B2B
    "юристы": ["юрист", "адвокат", "юридические услуги", "нотариус"],
    "бухгалтерия": ["бухгалтер", "бухгалтерские услуги", "accounting"],
    "it компании": ["it", "айти", "software", "разработка"],
    "строительство": ["строительная компания", "стройка", "ремонт"],
}


@dataclass
class ParsedQuery:
    """Распарсенный запрос."""
    original: str
    category: str
    location: str

    # Координаты (если город найден)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bbox: Optional[str] = None  # Bounding box для поиска

    # Нормализованная категория
    normalized_category: Optional[str] = None

    # Информация об исправлениях опечаток
    corrected_location: Optional[str] = None  # Исправленный город
    corrected_category: Optional[str] = None  # Исправленная категория
    used_llm: bool = False  # Использовался ли LLM для парсинга

    @property
    def is_valid(self) -> bool:
        """Валидный ли запрос."""
        return bool(self.category and self.location)

    @property
    def has_coordinates(self) -> bool:
        """Есть ли координаты."""
        return self.latitude is not None and self.longitude is not None

    @property
    def was_corrected(self) -> bool:
        """Были ли исправлены опечатки."""
        return self.corrected_location is not None or self.corrected_category is not None

    def get_correction_message(self) -> Optional[str]:
        """Сообщение об исправлениях для пользователя."""
        corrections = []
        if self.corrected_location:
            corrections.append(f"город: {self.corrected_location} → {self.location}")
        if self.corrected_category:
            corrections.append(f"категория: {self.corrected_category} → {self.category}")

        if corrections:
            return "✏️ Исправлено: " + ", ".join(corrections)
        return None


class QueryParser:
    """Парсер поисковых запросов с исправлением опечаток."""

    def __init__(
        self,
        llm_parser: Optional[Callable[[str], Awaitable[Optional[ParsedQuery]]]] = None,
        fuzzy_threshold: int = 2,
    ) -> None:
        """
        Инициализация парсера.

        Args:
            llm_parser: Опциональный LLM-парсер для сложных случаев
            fuzzy_threshold: Порог расстояния Левенштейна для fuzzy matching
        """
        self.llm_parser = llm_parser
        self.fuzzy_threshold = fuzzy_threshold

        # Создаём обратный индекс синонимов
        self._synonym_index: dict[str, str] = {}
        for main_category, synonyms in CATEGORY_SYNONYMS.items():
            self._synonym_index[main_category.lower()] = main_category
            for syn in synonyms:
                self._synonym_index[syn.lower()] = main_category

        # Список всех городов для fuzzy matching
        self._city_names = list(CITIES.keys())

        # Список всех категорий и синонимов для fuzzy matching
        self._all_categories = list(self._synonym_index.keys())

    def parse(self, query: str) -> ParsedQuery:
        """
        Парсит запрос вида "рестораны Сочи" или "автосервис в Москве".
        Автоматически исправляет опечатки.

        Args:
            query: Текстовый запрос пользователя

        Returns:
            ParsedQuery с разобранными компонентами
        """
        if not query:
            return ParsedQuery(original="", category="", location="")

        # Нормализуем
        query = query.strip()
        query_lower = query.lower()

        # Убираем предлоги
        query_clean = re.sub(r'\s+(в|на|по|из|для)\s+', ' ', query_lower)
        query_clean = query_clean.strip()

        # Разбиваем на слова
        words = query_clean.split()

        # Ищем город (с fuzzy matching)
        location = ""
        location_data = None
        corrected_location = None
        city_word_idx = -1

        for i, word in enumerate(words):
            # Сначала точное совпадение
            if word in CITIES:
                location = word.title()
                location_data = CITIES[word]
                city_word_idx = i
                break

            # Проверяем составные города (например "нижний новгород")
            if i < len(words) - 1:
                compound = f"{word} {words[i + 1]}"
                if compound in CITIES:
                    location = compound.title()
                    location_data = CITIES[compound]
                    city_word_idx = i
                    words.pop(i + 1)  # Удаляем второе слово
                    break

        # Если город не найден точно — пробуем fuzzy matching
        if not location:
            for i, word in enumerate(words):
                matched_city = fuzzy_find_best_match(
                    word, self._city_names, self.fuzzy_threshold
                )
                if matched_city:
                    corrected_location = word  # Сохраняем оригинал с опечаткой
                    location = matched_city.title()
                    location_data = CITIES[matched_city]
                    city_word_idx = i
                    logger.info(f"Typo corrected: '{word}' → '{matched_city}'")
                    break

        # Удаляем город из слов, чтобы осталась категория
        if city_word_idx >= 0:
            words.pop(city_word_idx)

        # То что осталось — категория
        category_raw = " ".join(words).strip()
        corrected_category = None

        # Нормализуем категорию (с fuzzy matching)
        normalized_category, corrected_category = self._normalize_category_fuzzy(category_raw)

        # Если нормализация нашла категорию, используем её
        category = normalized_category if normalized_category else category_raw

        # Создаём результат
        result = ParsedQuery(
            original=query,
            category=category,
            location=location,
            normalized_category=normalized_category,
            corrected_location=corrected_location,
            corrected_category=corrected_category,
        )

        # Добавляем координаты если город найден
        if location_data:
            result.latitude = location_data["lat"]
            result.longitude = location_data["lon"]
            result.bbox = location_data["bbox"]

        # Логируем исправления
        if result.was_corrected:
            logger.info(f"Query corrected: '{query}' → category='{category}', location='{location}'")

        return result

    async def parse_with_llm_fallback(self, query: str) -> ParsedQuery:
        """
        Парсит запрос, используя LLM как fallback для сложных случаев.

        Args:
            query: Текстовый запрос пользователя

        Returns:
            ParsedQuery
        """
        # Сначала пробуем обычный парсинг
        result = self.parse(query)

        # Если запрос не распознан и есть LLM — пробуем его
        if not result.is_valid and self.llm_parser:
            try:
                llm_result = await self.llm_parser(query)
                if llm_result and llm_result.is_valid:
                    llm_result.used_llm = True
                    logger.info(f"LLM parsed query: '{query}' → {llm_result}")
                    return llm_result
            except Exception as e:
                logger.warning(f"LLM parser failed: {e}")

        return result

    def _normalize_category_fuzzy(self, category: str) -> tuple[Optional[str], Optional[str]]:
        """
        Нормализует категорию к стандартному виду с fuzzy matching.

        Returns:
            Tuple (normalized_category, original_with_typo)
        """
        if not category:
            return None, None

        category_lower = category.lower().strip()

        # Прямое совпадение
        if category_lower in self._synonym_index:
            return self._synonym_index[category_lower], None

        # Частичное совпадение (подстрока)
        for syn, main in self._synonym_index.items():
            if syn in category_lower or category_lower in syn:
                return main, None

        # Fuzzy matching для каждого слова
        words = category_lower.split()
        for word in words:
            matched = fuzzy_find_best_match(word, self._all_categories, self.fuzzy_threshold)
            if matched and matched in self._synonym_index:
                return self._synonym_index[matched], word  # Возвращаем оригинал с опечаткой

        return None, None

    def _normalize_category(self, category: str) -> Optional[str]:
        """Нормализует категорию к стандартному виду (без fuzzy)."""
        normalized, _ = self._normalize_category_fuzzy(category)
        return normalized

    def suggest_cities(self, partial: str) -> list[str]:
        """Подсказки городов по началу ввода."""
        partial_lower = partial.lower()
        suggestions = []

        for city_name in CITIES.keys():
            if city_name.startswith(partial_lower):
                suggestions.append(city_name.title())

        return suggestions[:5]  # Максимум 5 подсказок

    def suggest_categories(self, partial: str) -> list[str]:
        """Подсказки категорий по началу ввода."""
        partial_lower = partial.lower()
        suggestions = set()

        for category in CATEGORY_SYNONYMS.keys():
            if category.startswith(partial_lower):
                suggestions.add(category.title())

        return list(suggestions)[:5]
