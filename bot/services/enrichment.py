"""Сервис обогащения данных компаний."""

import asyncio
import logging
import time
from typing import Callable, Optional, Awaitable

from bot.models.company import Company, EnrichmentStatus, EnrichmentResult
from bot.services.sherlock_client import (
    get_sherlock_client,
    is_telethon_configured,
    SherlockClientError,
    FloodWaitException,
)
from bot.services.sherlock_api import (
    get_sherlock_api_client,
    is_api_configured,
    SherlockAPIError,
    RateLimitError,
    InsufficientBalanceError,
    SherlockResponse,
)
from bot.services.phone_extractor import extract_phones, mask_phone
from bot.utils.config import settings

logger = logging.getLogger(__name__)

# Тип callback-функции для прогресса
ProgressCallback = Callable[[int, int, Optional[Company]], Awaitable[None]]


async def _query_sherlock(inn: str) -> Optional[SherlockResponse]:
    """
    Запрос к Sherlock через API (если настроен) или Telegram.

    Returns:
        SherlockResponse с данными или None

    Raises:
        FloodWaitException: При rate limit от Telegram
        RateLimitError: При rate limit от API (100 запросов/15мин)
        InsufficientBalanceError: При недостаточном балансе API
        SherlockClientError: При ошибке Telegram клиента
        SherlockAPIError: При ошибке API
    """
    # Приоритет: API > Telegram
    if is_api_configured():
        api_client = await get_sherlock_api_client()
        if api_client:
            return await api_client.query_with_retry(inn)

    # Fallback на Telegram (только если настроен)
    if not is_telethon_configured():
        raise SherlockClientError(
            "Ни API, ни Telethon не настроены. Укажите SHERLOCK_API_URL + SHERLOCK_API_KEY "
            "или TELETHON_API_ID + TELETHON_API_HASH + TELETHON_PHONE в .env"
        )

    # Telegram возвращает текст, создаём SherlockResponse
    client = await get_sherlock_client()
    text_response = await client.query_with_retry(inn)
    if text_response:
        phones = extract_phones(text_response)
        return SherlockResponse(
            query=inn,
            found=bool(phones),
            phones=phones,
            raw_data={"text": text_response},
        )
    return None


async def enrich_companies(
    companies: list[Company],
    progress_callback: Optional[ProgressCallback] = None,
    cancel_event: Optional[asyncio.Event] = None,
) -> EnrichmentResult:
    """
    Обогащает список компаний телефонами.

    Args:
        companies: Список компаний для обогащения
        progress_callback: Callback для отправки прогресса (current, total, last_company)
        cancel_event: Event для отмены обработки

    Returns:
        EnrichmentResult с результатами обработки
    """
    start_time = time.time()

    # Проверяем доступность клиентов
    using_api = is_api_configured()
    using_telethon = is_telethon_configured()

    if not using_api and not using_telethon:
        logger.error("Neither Sherlock API nor Telethon is configured")
        for company in companies:
            if company.status == EnrichmentStatus.PENDING:
                company.status = EnrichmentStatus.ERROR
        return EnrichmentResult(
            companies=companies,
            processing_time_seconds=time.time() - start_time,
        )

    if using_api:
        logger.info("Using Sherlock API for enrichment")
    else:
        # Инициализируем Telegram клиент
        try:
            await get_sherlock_client()
            logger.info("Using Sherlock Telegram bot for enrichment")
        except SherlockClientError as e:
            logger.error(f"Failed to start Sherlock client: {e}")
            for company in companies:
                if company.status == EnrichmentStatus.PENDING:
                    company.status = EnrichmentStatus.ERROR
            return EnrichmentResult(
                companies=companies,
                processing_time_seconds=time.time() - start_time,
            )

    processed = 0
    flood_wait_seconds = None

    for i, company in enumerate(companies):
        # Проверяем отмену
        if cancel_event and cancel_event.is_set():
            logger.info("Enrichment cancelled by user")
            break

        # Пропускаем невалидные ИНН
        if company.status == EnrichmentStatus.INVALID_INN:
            processed += 1
            continue

        # Запрос к Sherlock (API или Telegram)
        try:
            response = await _query_sherlock(company.inn)

            if response:
                company.raw_response = str(response.raw_data)
                company.records_count = response.counts

                # Заполняем все найденные данные
                if response.phones:
                    company.phone = ", ".join(response.phones)
                if response.emails:
                    company.emails = response.emails
                if response.names:
                    company.contact_names = response.names
                if response.addresses:
                    company.addresses = response.addresses
                if response.sources:
                    company.sources = response.sources

                # Статус — SUCCESS если нашли хоть что-то полезное
                if response.found:
                    company.status = EnrichmentStatus.SUCCESS
                    if response.phones:
                        logger.info(
                            f"Found phone for {company.inn}: {mask_phone(response.phones[0])}"
                        )
                    else:
                        logger.info(f"Found data for {company.inn} (no phone)")
                else:
                    company.status = EnrichmentStatus.NOT_FOUND
                    logger.debug(f"No data found for {company.inn}")
            else:
                company.status = EnrichmentStatus.NOT_FOUND
                logger.debug(f"No response for {company.inn}")

        except FloodWaitException as e:
            # FloodWait от Telegram — останавливаем обработку
            logger.warning(f"FloodWait received: need to wait {e.wait_seconds}s")
            flood_wait_seconds = e.wait_seconds
            company.status = EnrichmentStatus.ERROR
            processed += 1
            break

        except RateLimitError as e:
            # Rate limit от API — останавливаем обработку
            logger.warning(f"API rate limit: retry after {e.retry_after}s")
            flood_wait_seconds = e.retry_after
            company.status = EnrichmentStatus.ERROR
            processed += 1
            break

        except InsufficientBalanceError:
            # Недостаточный баланс API — останавливаем обработку
            logger.error("Insufficient API balance, stopping enrichment")
            company.status = EnrichmentStatus.ERROR
            processed += 1
            break

        except (SherlockClientError, SherlockAPIError) as e:
            logger.error(f"Sherlock error for {company.inn}: {e}")
            company.status = EnrichmentStatus.ERROR

        except Exception as e:
            logger.error(f"Unexpected error for {company.inn}: {e}")
            company.status = EnrichmentStatus.ERROR

        processed += 1

        # Callback для прогресса
        if progress_callback and (
            processed % settings.progress_update_interval == 0
            or processed == len(companies)
        ):
            try:
                await progress_callback(processed, len(companies), company)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

        # Задержка между запросами (антибан)
        if i < len(companies) - 1:  # Не ждём после последнего
            await asyncio.sleep(settings.request_delay_seconds)

    processing_time = time.time() - start_time
    was_interrupted = processed < len(companies)

    result = EnrichmentResult(
        companies=companies,
        processing_time_seconds=processing_time,
        flood_wait_seconds=flood_wait_seconds,
        was_interrupted=was_interrupted,
    )

    logger.info(
        f"Enrichment completed: {result.success_count}/{result.total} found, "
        f"{result.not_found_count} not found, {result.invalid_count} invalid, "
        f"{result.error_count} errors in {processing_time:.1f}s"
    )

    return result


async def enrich_single(company: Company) -> Company:
    """
    Обогащает одну компанию.

    Args:
        company: Компания для обогащения

    Returns:
        Обогащённая компания
    """
    result = await enrich_companies([company])
    return result.companies[0] if result.companies else company
