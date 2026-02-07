"""Скраппер 2ГИС через Playwright."""

import asyncio
import logging
import random
from typing import Optional
from urllib.parse import quote

from bot.services.scrapper.models import ScrapedCompany, ScrapperSource
from bot.services.scrapper.query_parser import ParsedQuery

logger = logging.getLogger(__name__)

# Селекторы 2ГИС (могут меняться)
SELECTORS = {
    "search_input": 'input[placeholder*="Поиск"]',
    "search_button": 'button[aria-label="Найти"]',
    "result_item": '._1hf7139',  # Карточка в списке
    "company_name": '._1al0wlf',  # Название
    "company_address": '._er2xx9',  # Адрес
    "company_phone": 'a[href^="tel:"]',  # Телефон
    "company_rating": '._y10azs',  # Рейтинг
    "company_reviews": '._jspzdp',  # Количество отзывов
    "load_more": '._1p8iqzw',  # Кнопка "Показать ещё"
    "no_results": '._12gyzmn',  # Нет результатов
}

# User-Agent для маскировки
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class TwoGisScrapper:
    """Скраппер 2ГИС."""

    def __init__(
        self,
        headless: bool = True,
        max_results: int = 100,
        delay_min: float = 1.0,
        delay_max: float = 3.0,
    ) -> None:
        """
        Инициализация скраппера.

        Args:
            headless: Запускать браузер в headless режиме
            max_results: Максимум результатов
            delay_min: Минимальная задержка между действиями
            delay_max: Максимальная задержка между действиями
        """
        self.headless = headless
        self.max_results = max_results
        self.delay_min = delay_min
        self.delay_max = delay_max
        self._browser = None
        self._context = None

    async def _get_delay(self) -> float:
        """Случайная задержка для антибана."""
        return random.uniform(self.delay_min, self.delay_max)

    async def _init_browser(self):
        """Инициализация браузера."""
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ]
            )

            # Создаём контекст с настройками
            self._context = await self._browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="ru-RU",
                timezone_id="Europe/Moscow",
            )

            # Антибан: убираем webdriver флаг
            await self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            logger.info("Browser initialized successfully")

        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            raise

    async def _close_browser(self):
        """Закрытие браузера."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if hasattr(self, '_playwright'):
            await self._playwright.stop()
        logger.info("Browser closed")

    async def scrape(self, query: ParsedQuery) -> list[ScrapedCompany]:
        """
        Скраппинг компаний из 2ГИС.

        Args:
            query: Распарсенный запрос

        Returns:
            Список спарсенных компаний
        """
        if not query.is_valid:
            logger.warning(f"Invalid query: {query.original}")
            return []

        companies: list[ScrapedCompany] = []

        try:
            await self._init_browser()
            page = await self._context.new_page()

            # Формируем URL поиска
            search_query = f"{query.category} {query.location}"
            encoded_query = quote(search_query)

            # 2ГИС URL с поиском
            url = f"https://2gis.ru/search/{encoded_query}"
            logger.info(f"Scraping 2GIS: {url}")

            # Переходим на страницу
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(await self._get_delay())

            # Ждём загрузки результатов
            try:
                await page.wait_for_selector(
                    SELECTORS["result_item"],
                    timeout=10000
                )
            except Exception:
                logger.warning("No results found or timeout")
                return []

            # Скроллим и собираем результаты
            collected = 0
            max_scrolls = 20
            scroll_count = 0

            while collected < self.max_results and scroll_count < max_scrolls:
                # Получаем все карточки на странице
                items = await page.query_selector_all(SELECTORS["result_item"])

                for item in items[collected:]:
                    if collected >= self.max_results:
                        break

                    try:
                        company = await self._parse_card(item)
                        if company:
                            companies.append(company)
                            collected += 1
                    except Exception as e:
                        logger.debug(f"Error parsing card: {e}")
                        continue

                # Скроллим вниз для подгрузки
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(await self._get_delay())

                # Проверяем есть ли кнопка "Показать ещё"
                load_more = await page.query_selector(SELECTORS["load_more"])
                if load_more:
                    try:
                        await load_more.click()
                        await asyncio.sleep(await self._get_delay())
                    except Exception:
                        pass

                scroll_count += 1

                # Проверяем не появились ли новые результаты
                new_items = await page.query_selector_all(SELECTORS["result_item"])
                if len(new_items) <= len(items):
                    # Больше результатов нет
                    break

            logger.info(f"Scraped {len(companies)} companies from 2GIS")

        except Exception as e:
            logger.error(f"Error scraping 2GIS: {e}")

        finally:
            await self._close_browser()

        return companies

    async def _parse_card(self, element) -> Optional[ScrapedCompany]:
        """
        Парсит карточку компании.

        Args:
            element: Playwright element

        Returns:
            ScrapedCompany или None
        """
        try:
            # Название
            name_el = await element.query_selector(SELECTORS["company_name"])
            name = await name_el.inner_text() if name_el else None

            if not name:
                return None

            # Адрес
            address_el = await element.query_selector(SELECTORS["company_address"])
            address = await address_el.inner_text() if address_el else ""

            # Телефон
            phone_el = await element.query_selector(SELECTORS["company_phone"])
            phone = None
            if phone_el:
                href = await phone_el.get_attribute("href")
                if href and href.startswith("tel:"):
                    phone = href.replace("tel:", "").strip()

            # Рейтинг
            rating = None
            rating_el = await element.query_selector(SELECTORS["company_rating"])
            if rating_el:
                try:
                    rating_text = await rating_el.inner_text()
                    rating = float(rating_text.replace(",", "."))
                except (ValueError, AttributeError):
                    pass

            # Количество отзывов
            reviews_count = None
            reviews_el = await element.query_selector(SELECTORS["company_reviews"])
            if reviews_el:
                try:
                    reviews_text = await reviews_el.inner_text()
                    # Извлекаем число из текста вида "123 отзыва"
                    import re
                    match = re.search(r'(\d+)', reviews_text)
                    if match:
                        reviews_count = int(match.group(1))
                except (ValueError, AttributeError):
                    pass

            return ScrapedCompany(
                name=name.strip(),
                address=address.strip(),
                phone=phone,
                rating=rating,
                reviews_count=reviews_count,
                source=ScrapperSource.TWOGIS,
            )

        except Exception as e:
            logger.debug(f"Error parsing card element: {e}")
            return None

    async def scrape_with_api(self, query: ParsedQuery) -> list[ScrapedCompany]:
        """
        Альтернативный метод через API 2ГИС (если доступен).

        Требует API ключ от 2ГИС.
        """
        # TODO: Реализовать если будет доступен API ключ
        # https://api.2gis.com/doc/maps/ru/quickstart/
        logger.warning("2GIS API method not implemented yet")
        return await self.scrape(query)
