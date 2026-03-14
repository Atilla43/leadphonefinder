"""Скраппер Яндекс.Карт через Playwright."""

import asyncio
import logging
import random
import re
from typing import Optional
from urllib.parse import quote
from bot.utils.config import settings
from bot.services.scrapper.models import ScrapedCompany, ScrapperSource
from bot.services.scrapper.query_parser import ParsedQuery

logger = logging.getLogger(__name__)

# User-Agent для маскировки
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# JavaScript для извлечения данных из DOM
JS_EXTRACT_COMPANIES = """() => {
    const results = [];
    const orgLinks = document.querySelectorAll('a[href*="/org/"]');
    const seen = new Set();

    for (const link of orgLinks) {
        const href = link.getAttribute('href');
        // Пропускаем ссылки на отзывы, галерею, меню
        if (href.includes('/reviews') || href.includes('/gallery') ||
            href.includes('/photos') || href.includes('/menu')) continue;
        if (seen.has(href)) continue;
        seen.add(href);

        // Находим родительскую карточку
        let card = link.closest('[class*="snippet"]');
        if (!card) card = link.parentElement ? link.parentElement.parentElement : null;
        if (!card) continue;

        const name = link.textContent.trim();
        if (!name || name.length < 2) continue;

        // Адрес
        let address = '';
        const addrEl = card.querySelector('[class*="address"]');
        if (addrEl) address = addrEl.textContent.trim();

        // Категория
        let category = '';
        const catEl = card.querySelector('[class*="category"]');
        if (catEl) category = catEl.textContent.trim();

        // Рейтинг — ищем паттерн X,X или X.X
        let rating = '';
        const ratingEl = card.querySelector('[class*="rating-badge-view__rating-text"], [class*="rating-text"]');
        if (ratingEl) {
            rating = ratingEl.textContent.trim();
        }

        // Количество отзывов
        let reviewsCount = '';
        const reviewsEl = card.querySelector('[class*="rating-count"], [class*="reviews-count"]');
        if (reviewsEl) {
            const text = reviewsEl.textContent.replace(/[^0-9]/g, '');
            if (text) reviewsCount = text;
        }

        results.push({name, href, address, category, rating, reviewsCount});
    }
    return results;
}"""


class YandexMapsScrapper:
    """Скраппер Яндекс.Карт."""

    def __init__(
        self,
        headless: bool = True,
        max_results: int = 100,
        delay_min: float = 1.5,
        delay_max: float = 4.0,
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
            # headless=False для обхода антибота Яндекса
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
        """Скраппинг компаний из Яндекс.Карт."""
        if not query.is_valid:
            logger.warning(f"Invalid query: {query.original}")
            return []

        companies: list[ScrapedCompany] = []

        try:
            await self._init_browser()
            page = await self._context.new_page()

            # Формируем URL — используем параметр text= для поиска
            search_query = f"{query.category} {query.location}"
            encoded_query = quote(search_query)

            # Пробуем yandex.com (yandex.ru может быть медленным через VPN)
            url = f"https://yandex.com/maps/?text={encoded_query}"
            logger.info(f"Scraping Yandex Maps: {url}")

            try:
                await page.goto(url, timeout=45000)
            except Exception as e:
                logger.warning(f"yandex.com failed: {e}, trying yandex.ru")
                url = f"https://yandex.ru/maps/?text={encoded_query}"
                await page.goto(url, timeout=45000)

            # Ждём полной загрузки SPA
            await asyncio.sleep(10)

            # Проверяем что страница загрузилась
            final_url = page.url
            logger.info(f"Final URL: {final_url}")

            if "captcha" in final_url.lower():
                logger.error("Yandex CAPTCHA detected!")
                return []

            # Собираем результаты со скроллом
            seen_names = set()
            scroll_count = 0
            no_new_results_count = 0

            # Шаг 0: логируем структуру DOM для дебага
            try:
                debug_info = await page.evaluate("""() => {
                    // Ищем скроллируемые контейнеры
                    const scrollable = [];
                    const all = document.querySelectorAll('*');
                    for (const el of all) {
                        if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
                            scrollable.push({
                                tag: el.tagName,
                                class: el.className.substring(0, 100),
                                scrollH: el.scrollHeight,
                                clientH: el.clientHeight,
                                childCount: el.children.length,
                            });
                        }
                    }
                    const orgCount = document.querySelectorAll('a[href*="/org/"]').length;
                    return {scrollable: scrollable.slice(0, 10), orgCount};
                }""")
                logger.info(f"DOM debug: orgLinks={debug_info['orgCount']}, "
                           f"scrollable containers: {len(debug_info['scrollable'])}")
                for sc in debug_info['scrollable'][:5]:
                    logger.info(f"  Scrollable: <{sc['tag']}> class='{sc['class'][:60]}' "
                               f"scrollH={sc['scrollH']} clientH={sc['clientH']} children={sc['childCount']}")
            except Exception as e:
                logger.warning(f"DOM debug error: {e}")

            while len(companies) < self.max_results:
                prev_count = len(companies)

                # Извлекаем данные из DOM
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

                    # Парсим рейтинг
                    rating = None
                    rating_str = item.get("rating", "")
                    if rating_str:
                        try:
                            rating = float(rating_str.replace(",", "."))
                        except ValueError:
                            pass

                    # Парсим отзывы
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
                        category=item.get("category", ""),
                        rating=rating,
                        reviews_count=reviews_count,
                        source=ScrapperSource.YANDEX,
                    )
                    companies.append(company)

                # Проверяем прогресс
                if len(companies) == prev_count:
                    no_new_results_count += 1
                    if no_new_results_count >= 4:
                        logger.info(f"No new results after {no_new_results_count} scrolls, stopping")
                        break
                else:
                    no_new_results_count = 0
                    logger.info(f"Found {len(companies)} companies after scroll {scroll_count}")

                # Скроллим боковую панель результатов (.scroll__container)
                try:
                    scroll_result = await page.evaluate("""() => {
                        // Прямой селектор — мы знаем класс из DOM debug
                        let panel = document.querySelector('.scroll__container');
                        if (panel && panel.scrollHeight > panel.clientHeight) {
                            const before = panel.scrollTop;
                            panel.scrollBy(0, 1500);
                            return {found: true, selector: '.scroll__container',
                                    before: before, after: panel.scrollTop,
                                    scrollH: panel.scrollHeight, clientH: panel.clientHeight};
                        }

                        // Fallback: ищем любой скроллируемый контейнер (не карту)
                        const all = document.querySelectorAll('div');
                        for (const el of all) {
                            if (el.scrollHeight > el.clientHeight + 200 &&
                                el.clientHeight > 300 &&
                                el.clientHeight < 1200 &&
                                !el.className.includes('map')) {
                                const before = el.scrollTop;
                                el.scrollBy(0, 1500);
                                return {found: true, selector: el.className.substring(0, 50),
                                        before: before, after: el.scrollTop,
                                        scrollH: el.scrollHeight, clientH: el.clientHeight};
                            }
                        }
                        return {found: false};
                    }""")
                    if scroll_result.get('found'):
                        logger.debug(
                            f"Scrolled '{scroll_result.get('selector')}': "
                            f"{scroll_result.get('before')}->{scroll_result.get('after')} "
                            f"(max={scroll_result.get('scrollH')})"
                        )
                    else:
                        logger.warning("No scrollable panel found!")
                except Exception as e:
                    logger.warning(f"Scroll error: {e}")

                # Ждём подгрузки новых элементов
                await asyncio.sleep(3)

                # Метод 2: Клик по пагинации / "Показать ещё" / "Найти ещё"
                try:
                    clicked = await page.evaluate("""() => {
                        // Ищем кнопки пагинации
                        const allClickable = document.querySelectorAll('button, a, [role="button"], span[class*="button"]');
                        for (const btn of allClickable) {
                            const text = (btn.textContent || '').toLowerCase().trim();
                            if (text.includes('показать ещё') || text.includes('показать еще') ||
                                text.includes('найти ещё') || text.includes('найти еще') ||
                                text.includes('следующая') || text.includes('дальше') ||
                                text.includes('show more') || text.includes('next') ||
                                text.includes('ещё') || text.includes('загрузить')) {
                                // Не кликаем по ссылкам типа "ещё N отзывов"
                                if (text.includes('отзыв') || text.includes('review')) continue;
                                btn.click();
                                return text;
                            }
                        }
                        return null;
                    }""")
                    if clicked:
                        logger.info(f"Clicked pagination: '{clicked}'")
                        await asyncio.sleep(4)
                except Exception:
                    pass

                await asyncio.sleep(1.5)
                scroll_count += 1

            logger.info(f"Scraped {len(companies)} companies from Yandex Maps")

        except Exception as e:
            logger.error(f"Error scraping Yandex Maps: {e}")

        finally:
            await self._close_browser()

        return companies
