"""Модуль скраппинга компаний из 2ГИС и Яндекс.Карт."""

from bot.services.scrapper.query_parser import QueryParser, ParsedQuery
from bot.services.scrapper.twogis import TwoGisScrapper
from bot.services.scrapper.yandex_maps import YandexMapsScrapper
from bot.services.scrapper.deduplicator import Deduplicator
from bot.services.scrapper.inn_finder import InnFinder
from bot.services.scrapper.models import ScrapedCompany, ScrapperResult

__all__ = [
    "QueryParser",
    "ParsedQuery",
    "TwoGisScrapper",
    "YandexMapsScrapper",
    "Deduplicator",
    "InnFinder",
    "ScrapedCompany",
    "ScrapperResult",
]
