"""Скраппер Яндекс.Карт через Playwright."""

import asyncio
import logging
import random
import re
from typing import Optional
from urllib.parse import quote

from bot.services.scrapper.models import ScrapedCompany, ScrapperSource
from bot.services.scrapper.query_parser import ParsedQuery

logger = logging.getLogger(__name__)

# Селекторы Яндекс.Карт (могут меняться)
SELECTORS = {
    "search_input": 'input.input__control',
    "search_button": 'button.small-search-form-view__button',
    "result_item": 'div.search-snippet-view',  # Карточка в списке
    "result_item_alt": 'li.search-list-view__item',
    "company_name": 'div.search-business-snippet-view__title',
    "company_name_alt": 'a.search-snippet-view__link-overlay',
    "company_address": 'div.search-business-snippet-view__address',
    "company_phone": 'a.search-business-snippet-view__phone',
    "company_rating": 'div.business-rating-badge-view__rating-text',
    "company_reviews": 'div.business-rating-badge-view__rating-count',
    "company_category": 'div.search-business-snippet-view__category',
    "load_more": 'div.add-business-view',
    "scroll_container": 'div.scroll__container',
}

# User-Agent для маскировки
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class YandexMapsScrapper:
    """Скраппер Яндекс.Карт."""

    def __init__(
        self,
        headless: bool = True,
        max_results: int = 100,
        delay_min: float = 1.5,
        delay_max: float = 4.0,
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

            # Создаём контекст
            self._context = await self._browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="ru-RU",
                timezone_id="Europe/Moscow",
            )

            # Антибан скрипт
            await self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = { runtime: {} };
            """)

            logger.info("Browser initialized for Yandex Maps")

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
        Скраппинг компаний из Яндекс.Карт.

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

            # Формируем URL
            search_query = f"{query.category} {query.location}"
            encoded_query = quote(search_query)

            # Яндекс.Карты URL
            url = f"https://yandex.ru/maps/search/{encoded_query}"
            logger.info(f"Scraping Yandex Maps: {url}")

            # Переходим
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(await self._get_delay())

            # Ждём загрузки результатов
            try:
                # Пробуем разные селекторы
                for selector in [SELECTORS["result_item"], SELECTORS["result_item_alt"]]:
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        break
                    except Exception:
                        continue
            except Exception:
                logger.warning("No results found on Yandex Maps")
                return []

            # Собираем результаты со скроллом
            collected = 0
            max_scrolls = 25
            scroll_count = 0
            seen_names = set()

            while collected < self.max_results and scroll_count < max_scrolls:
                # Получаем карточки
                items = await page.query_selector_all(SELECTORS["result_item"])
                if not items:
                    items = await page.query_selector_all(SELECTORS["result_item_alt"])

                for item in items:
                    if collected >= self.max_results:
                        break

                    try:
                        company = await self._parse_card(item, page)
                        if company and company.name not in seen_names:
                            companies.append(company)
                            seen_names.add(company.name)
                            collected += 1
                    except Exception as e:
                        logger.debug(f"Error parsing Yandex card: {e}")
                        continue

                # Скролл
                scroll_container = await page.query_selector(SELECTORS["scroll_container"])
                if scroll_container:
                    await scroll_container.evaluate("el => el.scrollBy(0, 400)")
                else:
                    await page.evaluate("window.scrollBy(0, 400)")

                await asyncio.sleep(await self._get_delay())
                scroll_count += 1

                # Проверяем появились ли новые
                new_items = await page.query_selector_all(SELECTORS["result_item"])
                if not new_items:
                    new_items = await page.query_selector_all(SELECTORS["result_item_alt"])

                if len(new_items) == len(items) and scroll_count > 3:
                    # Нет новых результатов
                    break

            logger.info(f"Scraped {len(companies)} companies from Yandex Maps")

        except Exception as e:
            logger.error(f"Error scraping Yandex Maps: {e}")

        finally:
            await self._close_browser()

        return companies

    async def _parse_card(self, element, page) -> Optional[ScrapedCompany]:
        """
        Парсит карточку компании.

        Args:
            element: Playwright element
            page: Текущая страница

        Returns:
            ScrapedCompany или None
        """
        try:
            # Название
            name = None
            for selector in [SELECTORS["company_name"], SELECTORS["company_name_alt"]]:
                name_el = await element.query_selector(selector)
                if name_el:
                    name = await name_el.inner_text()
                    break

            if not name:
                # Попробуем получить из атрибута
                name = await element.get_attribute("aria-label")

            if not name:
                return None

            # Адрес
            address = ""
            address_el = await element.query_selector(SELECTORS["company_address"])
            if address_el:
                address = await address_el.inner_text()

            # Категория
            category = None
            category_el = await element.query_selector(SELECTORS["company_category"])
            if category_el:
                category = await category_el.inner_text()

            # Рейтинг
            rating = None
            rating_el = await element.query_selector(SELECTORS["company_rating"])
            if rating_el:
                try:
                    rating_text = await rating_el.inner_text()
                    rating = float(rating_text.replace(",", "."))
                except (ValueError, AttributeError):
                    pass

            # Отзывы
            reviews_count = None
            reviews_el = await element.query_selector(SELECTORS["company_reviews"])
            if reviews_el:
                try:
                    reviews_text = await reviews_el.inner_text()
                    match = re.search(r'(\d+)', reviews_text.replace(" ", ""))
                    if match:
                        reviews_count = int(match.group(1))
                except (ValueError, AttributeError):
                    pass

            # Телефон (часто скрыт, нужно кликнуть на карточку)
            phone = None
            phone_el = await element.query_selector(SELECTORS["company_phone"])
            if phone_el:
                phone_text = await phone_el.inner_text()
                # Нормализуем телефон
                phone = re.sub(r'[^\d+]', '', phone_text)

            return ScrapedCompany(
                name=name.strip(),
                address=address.strip() if address else "",
                phone=phone,
                category=category,
                rating=rating,
                reviews_count=reviews_count,
                source=ScrapperSource.YANDEX,
            )

        except Exception as e:
            logger.debug(f"Error parsing Yandex card element: {e}")
            return None

    async def get_company_details(self, page, company_url: str) -> dict:
        """
        Получает детальную информацию о компании (телефон, сайт, часы работы).

        Требует перехода на страницу компании.
        """
        details = {}

        try:
            await page.goto(company_url, wait_until="networkidle", timeout=20000)
            await asyncio.sleep(await self._get_delay())

            # Телефон
            phone_el = await page.query_selector('a[href^="tel:"]')
            if phone_el:
                href = await phone_el.get_attribute("href")
                details["phone"] = href.replace("tel:", "")

            # Сайт
            website_el = await page.query_selector('a.business-urls-view__link')
            if website_el:
                details["website"] = await website_el.get_attribute("href")

            # Часы работы
            hours_el = await page.query_selector('div.business-working-status-view')
            if hours_el:
                details["working_hours"] = await hours_el.inner_text()

        except Exception as e:
            logger.debug(f"Error getting company details: {e}")

        return details
