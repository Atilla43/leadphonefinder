"""Оркестратор скраппинга - объединяет все компоненты."""

import asyncio
import logging
from datetime import datetime
from typing import Callable, Optional

from bot.services.scrapper.models import ScrapedCompany, ScrapperResult, ScrapperSource
from bot.services.scrapper.query_parser import QueryParser, ParsedQuery
from bot.services.scrapper.twogis import TwoGisScrapper
from bot.services.scrapper.yandex_maps import YandexMapsScrapper
from bot.services.scrapper.deduplicator import Deduplicator
from bot.services.scrapper.inn_finder import InnFinder

logger = logging.getLogger(__name__)

# Тип для callback прогресса
ProgressCallback = Callable[[str, int, int], None]


class ScrapperOrchestrator:
    """
    Оркестратор скраппинга.

    Координирует работу:
    1. QueryParser - разбор запроса
    2. TwoGisScrapper / YandexMapsScrapper - сбор данных
    3. Deduplicator - удаление дубликатов
    4. InnFinder - поиск ИНН
    """

    def __init__(
        self,
        max_results: int = 100,
        use_twogis: bool = True,
        use_yandex: bool = True,
        headless: bool = True,
        dadata_token: Optional[str] = None,
        find_inn: bool = True,
    ) -> None:
        """
        Инициализация оркестратора.

        Args:
            max_results: Максимум результатов с каждого источника
            use_twogis: Использовать 2ГИС
            use_yandex: Использовать Яндекс.Карты
            headless: Headless режим браузера
            dadata_token: Токен DaData для поиска ИНН
            find_inn: Искать ИНН для компаний
        """
        self.max_results = max_results
        self.use_twogis = use_twogis
        self.use_yandex = use_yandex
        self.headless = headless
        self.find_inn = find_inn

        # Компоненты
        self.query_parser = QueryParser()
        self.deduplicator = Deduplicator()
        self.inn_finder = InnFinder(dadata_token=dadata_token) if find_inn else None

    async def scrape(
        self,
        query: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ScrapperResult:
        """
        Выполняет полный цикл скраппинга.

        Args:
            query: Поисковый запрос (например "рестораны Сочи")
            progress_callback: Callback для отслеживания прогресса

        Returns:
            ScrapperResult с результатами
        """
        result = ScrapperResult(
            query=query,
            companies=[],
            started_at=datetime.now(),
        )

        try:
            # 1. Парсим запрос
            if progress_callback:
                await progress_callback("Анализ запроса...", 0, 100)

            parsed = self.query_parser.parse(query)

            if not parsed.is_valid:
                result.errors.append(
                    f"Не удалось разобрать запрос. "
                    f"Укажите категорию и город, например: 'рестораны Сочи'"
                )
                return result

            logger.info(f"Parsed query: {parsed.category} in {parsed.location}")

            # 2. Собираем данные из источников
            all_companies: list[ScrapedCompany] = []

            # 2ГИС
            if self.use_twogis:
                if progress_callback:
                    await progress_callback("Поиск в 2ГИС...", 10, 100)

                try:
                    twogis = TwoGisScrapper(
                        headless=self.headless,
                        max_results=self.max_results,
                    )
                    twogis_companies = await twogis.scrape(parsed)
                    all_companies.extend(twogis_companies)
                    result.from_twogis = len(twogis_companies)
                    logger.info(f"2GIS: found {len(twogis_companies)} companies")
                except Exception as e:
                    logger.error(f"2GIS scraping error: {e}")
                    result.errors.append(f"Ошибка 2ГИС: {str(e)}")

            # Яндекс.Карты
            if self.use_yandex:
                if progress_callback:
                    await progress_callback("Поиск в Яндекс.Картах...", 40, 100)

                try:
                    yandex = YandexMapsScrapper(
                        headless=self.headless,
                        max_results=self.max_results,
                    )
                    yandex_companies = await yandex.scrape(parsed)
                    all_companies.extend(yandex_companies)
                    result.from_yandex = len(yandex_companies)
                    logger.info(f"Yandex: found {len(yandex_companies)} companies")
                except Exception as e:
                    logger.error(f"Yandex scraping error: {e}")
                    result.errors.append(f"Ошибка Яндекс.Карт: {str(e)}")

            result.total_found = len(all_companies)

            if not all_companies:
                result.errors.append("Компании не найдены")
                return result

            # 3. Дедупликация
            if progress_callback:
                await progress_callback("Удаление дубликатов...", 70, 100)

            unique_companies, duplicates = self.deduplicator.deduplicate(all_companies)
            result.duplicates_removed = duplicates
            logger.info(f"After deduplication: {len(unique_companies)} unique")

            # 4. Поиск ИНН
            if self.find_inn and self.inn_finder:
                if progress_callback:
                    await progress_callback("Поиск ИНН компаний...", 80, 100)

                try:
                    found_inn, not_found_inn = await self.inn_finder.enrich_companies(
                        unique_companies
                    )
                    logger.info(f"INN: found {found_inn}, not found {not_found_inn}")
                except Exception as e:
                    logger.error(f"INN search error: {e}")
                    result.errors.append(f"Ошибка поиска ИНН: {str(e)}")
                finally:
                    await self.inn_finder.close()

            # 5. Готово
            result.companies = unique_companies
            result.finished_at = datetime.now()

            if progress_callback:
                await progress_callback("Готово!", 100, 100)

            logger.info(
                f"Scraping completed: {len(result.companies)} companies, "
                f"duration: {result.duration_seconds:.1f}s"
            )

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            result.errors.append(f"Ошибка: {str(e)}")
            result.finished_at = datetime.now()

        return result

    async def scrape_parallel(
        self,
        query: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ScrapperResult:
        """
        Параллельный скраппинг из всех источников.

        Быстрее чем последовательный, но требует больше ресурсов.
        """
        result = ScrapperResult(
            query=query,
            companies=[],
            started_at=datetime.now(),
        )

        try:
            # Парсим запрос
            parsed = self.query_parser.parse(query)

            if not parsed.is_valid:
                result.errors.append("Не удалось разобрать запрос")
                return result

            # Запускаем скрапперы параллельно
            tasks = []

            if self.use_twogis:
                twogis = TwoGisScrapper(
                    headless=self.headless,
                    max_results=self.max_results,
                )
                tasks.append(("2gis", twogis.scrape(parsed)))

            if self.use_yandex:
                yandex = YandexMapsScrapper(
                    headless=self.headless,
                    max_results=self.max_results,
                )
                tasks.append(("yandex", yandex.scrape(parsed)))

            if progress_callback:
                await progress_callback("Поиск компаний...", 20, 100)

            # Ждём результаты
            all_companies: list[ScrapedCompany] = []

            results = await asyncio.gather(
                *[task for _, task in tasks],
                return_exceptions=True
            )

            for (source, _), res in zip(tasks, results):
                if isinstance(res, Exception):
                    logger.error(f"{source} error: {res}")
                    result.errors.append(f"Ошибка {source}: {str(res)}")
                else:
                    all_companies.extend(res)
                    if source == "2gis":
                        result.from_twogis = len(res)
                    else:
                        result.from_yandex = len(res)

            result.total_found = len(all_companies)

            # Дедупликация
            if progress_callback:
                await progress_callback("Обработка результатов...", 70, 100)

            unique, duplicates = self.deduplicator.deduplicate(all_companies)
            result.duplicates_removed = duplicates

            # Поиск ИНН
            if self.find_inn and self.inn_finder and unique:
                if progress_callback:
                    await progress_callback("Поиск ИНН...", 85, 100)

                try:
                    await self.inn_finder.enrich_companies(unique)
                finally:
                    await self.inn_finder.close()

            result.companies = unique
            result.finished_at = datetime.now()

            if progress_callback:
                await progress_callback("Готово!", 100, 100)

        except Exception as e:
            logger.error(f"Parallel scraping error: {e}")
            result.errors.append(str(e))
            result.finished_at = datetime.now()

        return result


async def quick_scrape(
    query: str,
    max_results: int = 50,
    use_twogis: bool = True,
    use_yandex: bool = True,
) -> ScrapperResult:
    """
    Быстрый скраппинг без поиска ИНН.

    Args:
        query: Поисковый запрос
        max_results: Максимум результатов
        use_twogis: Использовать 2ГИС
        use_yandex: Использовать Яндекс

    Returns:
        ScrapperResult
    """
    orchestrator = ScrapperOrchestrator(
        max_results=max_results,
        use_twogis=use_twogis,
        use_yandex=use_yandex,
        find_inn=False,
    )
    return await orchestrator.scrape(query)
