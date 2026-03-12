"""Скраппер 2ГИС через Playwright."""

import asyncio
import logging
import random
from typing import Optional
from urllib.parse import quote

from bot.services.scrapper.models import ScrapedCompany, ScrapperSource
from bot.services.scrapper.query_parser import ParsedQuery

logger = logging.getLogger(__name__)

# User-Agent для маскировки
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# JavaScript для извлечения данных из DOM
JS_EXTRACT_COMPANIES = """() => {
    const results = [];
    // 2GIS использует ссылки вида /firm/ID
    const firmLinks = document.querySelectorAll('a[href*="/firm/"]');
    const seen = new Set();

    for (const link of firmLinks) {
        const href = link.getAttribute('href');
        if (seen.has(href)) continue;
        seen.add(href);

        const name = link.textContent.trim();
        if (!name || name.length < 2) continue;

        // Ищем родительскую карточку
        let card = link.closest('[class*="result"], [class*="item"], [class*="card"]');
        if (!card) card = link.parentElement ? link.parentElement.parentElement : null;
        if (!card) continue;

        // Адрес
        let address = '';
        const addrEl = card.querySelector('[class*="address"]');
        if (addrEl) address = addrEl.textContent.trim();

        // Рейтинг
        let rating = '';
        const allText = card.textContent;
        const ratingMatch = allText.match(/(\\d[,.]\\d)/);
        if (ratingMatch) rating = ratingMatch[1];

        // Категория
        let category = '';
        const catEl = card.querySelector('[class*="rubric"], [class*="category"]');
        if (catEl) category = catEl.textContent.trim();

        // Кол-во отзывов
        let reviewsCount = '';
        const reviewsEl = card.querySelector('[class*="review"], [class*="comment"]');
        if (reviewsEl) {
            const text = reviewsEl.textContent.replace(/[^0-9]/g, '');
            if (text) reviewsCount = text;
        }

        // Телефон
        let phone = '';
        const phoneEl = card.querySelector('a[href^="tel:"]');
        if (phoneEl) {
            const phoneHref = phoneEl.getAttribute('href');
            phone = phoneHref.replace('tel:', '').trim();
        }

        results.push({name, href, address, rating, phone, category, reviewsCount});
    }
    return results;
}"""


class TwoGisScrapper:
    """Скраппер 2ГИС."""

    def __init__(
        self,
        headless: bool = True,
        max_results: int = 100,
        delay_min: float = 1.0,
        delay_max: float = 3.0,
    ) -> None:
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
            # 2ГИС блокирует headless — используем non-headless
            self._browser = await self._playwright.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ]
            )

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
        """Скраппинг компаний из 2ГИС."""
        if not query.is_valid:
            logger.warning(f"Invalid query: {query.original}")
            return []

        companies: list[ScrapedCompany] = []

        try:
            await self._init_browser()
            page = await self._context.new_page()

            # Формируем URL — через город/search
            search_query = f"{query.category} {query.location}"
            encoded_query = quote(search_query)

            url = f"https://2gis.ru/search/{encoded_query}"
            logger.info(f"Scraping 2GIS: {url}")

            await page.goto(url, timeout=30000)
            await asyncio.sleep(8)  # Ждём загрузки SPA

            # Проверяем на антибот
            final_url = page.url
            page_text = await page.content()

            if "Forbidden" in page_text or "captcha" in final_url.lower():
                logger.warning("2GIS antibot detected! IP may be blocked.")
                return []

            # Собираем результаты со скроллом
            seen_names = set()
            max_scrolls = 15
            scroll_count = 0
            prev_count = 0

            while len(companies) < self.max_results and scroll_count < max_scrolls:
                try:
                    raw_data = await page.evaluate(JS_EXTRACT_COMPANIES)
                except Exception as e:
                    logger.warning(f"JS evaluation error: {e}")
                    break

                for item in raw_data:
                    name = item.get("name", "").strip()
                    if not name or name in seen_names:
                        continue
                    if len(companies) >= self.max_results:
                        break

                    seen_names.add(name)

                    # Рейтинг
                    rating = None
                    rating_str = item.get("rating", "")
                    if rating_str:
                        try:
                            rating = float(rating_str.replace(",", "."))
                        except ValueError:
                            pass

                    # Кол-во отзывов
                    reviews_count = None
                    reviews_str = item.get("reviewsCount", "")
                    if reviews_str:
                        try:
                            reviews_count = int(reviews_str)
                        except ValueError:
                            pass

                    company = ScrapedCompany(
                        name=name,
                        address=item.get("address", ""),
                        phone=item.get("phone", "") or None,
                        rating=rating,
                        reviews_count=reviews_count,
                        category=item.get("category", "") or None,
                        source=ScrapperSource.TWOGIS,
                    )
                    companies.append(company)

                if len(companies) == prev_count and scroll_count > 2:
                    break
                prev_count = len(companies)

                # Скроллим
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(await self._get_delay())
                scroll_count += 1

            logger.info(f"Scraped {len(companies)} companies from 2GIS")

        except Exception as e:
            logger.error(f"Error scraping 2GIS: {e}")

        finally:
            await self._close_browser()

        return companies
