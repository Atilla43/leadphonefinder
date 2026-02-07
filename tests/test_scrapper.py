"""Тесты модуля скраппера."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.services.scrapper.query_parser import (
    QueryParser,
    ParsedQuery,
    CITIES,
    levenshtein_distance,
    fuzzy_find_best_match,
)
from bot.services.scrapper.deduplicator import (
    Deduplicator,
    normalize_name,
    normalize_address,
    normalize_phone,
    fuzzy_match,
)
from bot.services.scrapper.models import ScrapedCompany, ScrapperSource


class TestQueryParser:
    """Тесты парсера запросов."""

    def setup_method(self):
        """Инициализация парсера."""
        self.parser = QueryParser()

    def test_simple_query(self):
        """Простой запрос: категория + город."""
        result = self.parser.parse("рестораны Сочи")

        assert result.is_valid
        assert result.category == "рестораны"
        assert result.location == "Сочи"
        assert result.has_coordinates

    def test_query_with_preposition(self):
        """Запрос с предлогом."""
        result = self.parser.parse("автосервисы в Москве")

        assert result.is_valid
        assert "автосервис" in result.category
        assert result.location == "Москва"

    def test_city_alias(self):
        """Сокращённые названия городов."""
        result = self.parser.parse("кафе спб")

        assert result.is_valid
        assert result.location == "Спб"
        assert result.has_coordinates

    def test_category_normalization(self):
        """Нормализация категорий."""
        result = self.parser.parse("ресторан Казань")

        assert result.normalized_category == "рестораны"

    def test_invalid_query_no_city(self):
        """Запрос без города."""
        result = self.parser.parse("рестораны")

        assert not result.is_valid
        assert not result.location

    def test_invalid_query_empty(self):
        """Пустой запрос."""
        result = self.parser.parse("")

        assert not result.is_valid

    def test_city_coordinates(self):
        """Координаты города."""
        result = self.parser.parse("кафе Москва")

        assert result.latitude == CITIES["москва"]["lat"]
        assert result.longitude == CITIES["москва"]["lon"]
        assert result.bbox == CITIES["москва"]["bbox"]

    def test_suggest_cities(self):
        """Подсказки городов."""
        suggestions = self.parser.suggest_cities("моск")

        assert "Москва" in suggestions

    def test_suggest_categories(self):
        """Подсказки категорий."""
        suggestions = self.parser.suggest_categories("рест")

        assert "Рестораны" in suggestions

    # === ТЕСТЫ ИСПРАВЛЕНИЯ ОПЕЧАТОК ===

    def test_typo_city_sochi(self):
        """Опечатка в названии города: Сачи → Сочи."""
        result = self.parser.parse("рестораны Сачи")

        assert result.is_valid
        assert result.location == "Сочи"
        assert result.corrected_location == "сачи"
        assert result.was_corrected

    def test_typo_city_moscow(self):
        """Опечатка в названии города: Масква → Москва."""
        result = self.parser.parse("кафе Масква")

        assert result.is_valid
        assert result.location == "Москва"
        assert result.corrected_location == "масква"

    def test_typo_category_restaurants(self):
        """Опечатка в категории: рестараны → рестораны."""
        result = self.parser.parse("рестараны Москва")

        assert result.is_valid
        assert result.normalized_category == "рестораны"
        assert result.corrected_category == "рестараны"

    def test_typo_category_autoservice(self):
        """Опечатка в категории: афтосервис → автосервисы."""
        result = self.parser.parse("афтосервис Казань")

        assert result.is_valid
        assert result.normalized_category == "автосервисы"

    def test_no_correction_needed(self):
        """Без опечаток — коррекция не нужна."""
        result = self.parser.parse("рестораны Сочи")

        assert result.is_valid
        assert not result.was_corrected
        assert result.corrected_location is None
        assert result.corrected_category is None

    def test_correction_message(self):
        """Сообщение об исправлении."""
        result = self.parser.parse("рестараны Сачи")

        assert result.was_corrected
        msg = result.get_correction_message()
        assert msg is not None
        assert "Исправлено" in msg

    def test_multiple_typos(self):
        """Несколько опечаток одновременно."""
        result = self.parser.parse("рестараны Масква")

        assert result.is_valid
        assert result.location == "Москва"
        assert result.normalized_category == "рестораны"


class TestLevenshteinDistance:
    """Тесты расстояния Левенштейна."""

    def test_identical_strings(self):
        """Одинаковые строки."""
        assert levenshtein_distance("москва", "москва") == 0

    def test_one_char_difference(self):
        """Разница в один символ."""
        assert levenshtein_distance("сочи", "сачи") == 1
        assert levenshtein_distance("москва", "масква") == 1

    def test_two_char_difference(self):
        """Разница в два символа."""
        assert levenshtein_distance("рестораны", "рестараны") == 1
        assert levenshtein_distance("казань", "козань") == 1

    def test_empty_string(self):
        """Пустая строка."""
        assert levenshtein_distance("", "тест") == 4
        assert levenshtein_distance("тест", "") == 4


class TestFuzzyFindBestMatch:
    """Тесты fuzzy поиска."""

    def test_exact_match(self):
        """Точное совпадение."""
        candidates = ["москва", "сочи", "казань"]
        assert fuzzy_find_best_match("москва", candidates) == "москва"

    def test_typo_match(self):
        """Совпадение с опечаткой."""
        candidates = ["москва", "сочи", "казань"]
        assert fuzzy_find_best_match("масква", candidates) == "москва"
        assert fuzzy_find_best_match("сачи", candidates) == "сочи"

    def test_no_match(self):
        """Нет подходящего совпадения."""
        candidates = ["москва", "сочи", "казань"]
        assert fuzzy_find_best_match("владивосток", candidates) is None

    def test_threshold(self):
        """Порог расстояния."""
        candidates = ["екатеринбург"]
        # Слишком много ошибок
        assert fuzzy_find_best_match("екотиренбург", candidates, max_distance=1) is None
        # Допустимо с большим порогом
        assert fuzzy_find_best_match("екотиренбург", candidates, max_distance=3) == "екатеринбург"


class TestNormalization:
    """Тесты нормализации данных."""

    @pytest.mark.parametrize(
        "name,expected",
        [
            ('ООО "Ромашка"', "ромашка"),
            ("ИП Иванов", "иванов"),
            ('ЗАО «Тест»', "тест"),
            ("Кафе Пушкин", "кафе пушкин"),
            ("  Пробелы  ", "пробелы"),
        ],
    )
    def test_normalize_name(self, name: str, expected: str):
        """Нормализация названий."""
        assert normalize_name(name) == expected

    @pytest.mark.parametrize(
        "address,expected",
        [
            ("123456, улица Ленина, 1", "ул ленина 1"),
            ("г. Москва, проспект Мира, д. 10", "г москва пр мира д 10"),
            ("ул. Тверская, д. 1, корпус 2", "ул тверская д 1 к 2"),
        ],
    )
    def test_normalize_address(self, address: str, expected: str):
        """Нормализация адресов."""
        result = normalize_address(address)
        # Проверяем ключевые части
        for part in expected.split():
            assert part in result

    @pytest.mark.parametrize(
        "phone,expected",
        [
            ("+79161234567", "+79161234567"),
            ("89161234567", "+79161234567"),
            ("8 (916) 123-45-67", "+79161234567"),
            ("+7 916 123 45 67", "+79161234567"),
            ("", None),
            (None, None),
        ],
    )
    def test_normalize_phone(self, phone, expected):
        """Нормализация телефонов."""
        assert normalize_phone(phone) == expected


class TestFuzzyMatch:
    """Тесты нечёткого сравнения."""

    def test_exact_match(self):
        """Точное совпадение."""
        assert fuzzy_match("кафе пушкин", "кафе пушкин")

    def test_substring_match(self):
        """Одна строка содержит другую."""
        assert fuzzy_match("кафе пушкин", "кафе пушкин на тверской")

    def test_similar_strings(self):
        """Похожие строки."""
        assert fuzzy_match("ресторан итальянский", "ресторан италианский", 0.8)

    def test_different_strings(self):
        """Разные строки."""
        assert not fuzzy_match("кафе", "автосервис")

    def test_empty_strings(self):
        """Пустые строки."""
        assert not fuzzy_match("", "тест")
        assert not fuzzy_match("тест", "")


class TestDeduplicator:
    """Тесты дедупликатора."""

    def setup_method(self):
        """Инициализация."""
        self.deduplicator = Deduplicator()

    def test_no_duplicates(self):
        """Без дубликатов."""
        companies = [
            ScrapedCompany(name="Компания 1", address="Адрес 1", source=ScrapperSource.TWOGIS),
            ScrapedCompany(name="Компания 2", address="Адрес 2", source=ScrapperSource.YANDEX),
        ]

        unique, count = self.deduplicator.deduplicate(companies)

        assert len(unique) == 2
        assert count == 0

    def test_exact_duplicates(self):
        """Точные дубликаты."""
        companies = [
            ScrapedCompany(name="Кафе Пушкин", address="Тверской бульвар, 26", source=ScrapperSource.TWOGIS),
            ScrapedCompany(name="Кафе Пушкин", address="Тверской бульвар, 26", source=ScrapperSource.YANDEX),
        ]

        unique, count = self.deduplicator.deduplicate(companies)

        assert len(unique) == 1
        assert count == 1

    def test_duplicate_by_inn(self):
        """Дубликат по ИНН."""
        companies = [
            ScrapedCompany(name="Сбербанк", address="Москва", inn="7707083893", source=ScrapperSource.TWOGIS),
            ScrapedCompany(name="ПАО Сбербанк", address="Москва, ул. Вавилова", inn="7707083893", source=ScrapperSource.YANDEX),
        ]

        unique, count = self.deduplicator.deduplicate(companies)

        assert len(unique) == 1
        assert count == 1

    def test_duplicate_by_phone(self):
        """Дубликат по телефону."""
        companies = [
            ScrapedCompany(name="Ресторан А", address="Адрес 1", phone="+79161234567", source=ScrapperSource.TWOGIS),
            ScrapedCompany(name="Ресторан Б", address="Адрес 2", phone="89161234567", source=ScrapperSource.YANDEX),
        ]

        unique, count = self.deduplicator.deduplicate(companies)

        assert len(unique) == 1
        assert count == 1

    def test_merge_data(self):
        """Объединение данных при дедупликации."""
        companies = [
            ScrapedCompany(
                name="Кафе Тест",
                address="Москва, ул. Тестовая, 1",
                phone=None,
                rating=4.5,
                source=ScrapperSource.TWOGIS,
            ),
            ScrapedCompany(
                name="Кафе Тест",
                address="Москва, ул. Тестовая, 1",
                phone="+79161234567",
                rating=4.2,
                website="http://test.ru",
                source=ScrapperSource.YANDEX,
            ),
        ]

        unique, _ = self.deduplicator.deduplicate(companies)

        assert len(unique) == 1
        # Телефон должен быть взят из второй записи
        assert unique[0].phone == "+79161234567"
        # Рейтинг - выше (из первой)
        assert unique[0].rating == 4.5
        # Сайт - из второй
        assert unique[0].website == "http://test.ru"

    def test_empty_list(self):
        """Пустой список."""
        unique, count = self.deduplicator.deduplicate([])

        assert len(unique) == 0
        assert count == 0


class TestScrapedCompany:
    """Тесты модели ScrapedCompany."""

    def test_hash_equality(self):
        """Хеш для одинаковых компаний."""
        c1 = ScrapedCompany(name="Тест", address="Адрес", source=ScrapperSource.TWOGIS)
        c2 = ScrapedCompany(name="ТЕСТ", address="АДРЕС", source=ScrapperSource.YANDEX)

        assert hash(c1) == hash(c2)
        assert c1 == c2

    def test_hash_inequality(self):
        """Хеш для разных компаний."""
        c1 = ScrapedCompany(name="Тест 1", address="Адрес 1", source=ScrapperSource.TWOGIS)
        c2 = ScrapedCompany(name="Тест 2", address="Адрес 2", source=ScrapperSource.TWOGIS)

        assert hash(c1) != hash(c2)
        assert c1 != c2
