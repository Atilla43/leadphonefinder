"""Обработчик команд скраппера."""

import asyncio
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.services.scrapper.orchestrator import ScrapperOrchestrator
from bot.services.scrapper.query_parser import QueryParser
from bot.services.scrapper.models import ScrapperResult
from bot.services.enrichment import enrich_single
from bot.services.result_generator import generate_excel
from bot.utils.config import settings
from bot.ui.keyboards import get_scrapper_keyboard, get_source_keyboard
from bot.ui.messages import (
    SCRAPPER_START,
    SCRAPPER_PROGRESS,
    SCRAPPER_COMPLETE,
    SCRAPPER_ERROR,
)

logger = logging.getLogger(__name__)
router = Router()


class ScrapperStates(StatesGroup):
    """Состояния FSM для скраппера."""
    waiting_query = State()
    selecting_source = State()
    scrapping = State()
    enriching = State()


# Хранилище активных задач скраппинга
active_tasks: dict[int, ScrapperResult] = {}


@router.message(Command("scrape"))
async def cmd_scrape(message: Message, state: FSMContext) -> None:
    """Команда /scrape - начало скраппинга."""
    # Проверка whitelist
    if settings.allowed_users and message.from_user.id not in settings.allowed_users:
        await message.answer("⛔ У вас нет доступа к этой функции.")
        return

    await state.set_state(ScrapperStates.waiting_query)

    await message.answer(
        "🔍 <b>Поиск компаний</b>\n\n"
        "Введите запрос для поиска, например:\n"
        "• <code>рестораны Сочи</code>\n"
        "• <code>автосервисы Москва</code>\n"
        "• <code>салоны красоты Казань</code>\n\n"
        "Или выберите популярный запрос:",
        reply_markup=get_scrapper_keyboard(),
    )


@router.message(ScrapperStates.waiting_query)
async def process_query(message: Message, state: FSMContext) -> None:
    """Обработка поискового запроса."""
    query = message.text.strip()

    if not query:
        await message.answer("❌ Введите поисковый запрос")
        return

    # Проверяем запрос (с fuzzy matching для исправления опечаток)
    parser = QueryParser()
    parsed = parser.parse(query)

    if not parsed.is_valid:
        suggestions = []
        if not parsed.location:
            suggestions.append("• Укажите город (Москва, Сочи, Казань...)")
        if not parsed.category:
            suggestions.append("• Укажите категорию (рестораны, автосервисы...)")

        await message.answer(
            "❌ <b>Не удалось разобрать запрос</b>\n\n"
            "Проверьте:\n" + "\n".join(suggestions) + "\n\n"
            "Пример: <code>рестораны Сочи</code>"
        )
        return

    # Сохраняем запрос
    await state.update_data(query=query, parsed=parsed)
    await state.set_state(ScrapperStates.selecting_source)

    # Формируем ответ
    response_lines = [
        f"📍 <b>Запрос:</b> {query}",
    ]

    # Если были исправлены опечатки — показываем пользователю
    correction_msg = parsed.get_correction_message()
    if correction_msg:
        response_lines.append(f"\n{correction_msg}\n")

    response_lines.extend([
        f"📂 <b>Категория:</b> {parsed.category}",
        f"🏙 <b>Город:</b> {parsed.location}",
        "",
        "Выберите источники данных:",
    ])

    await message.answer(
        "\n".join(response_lines),
        reply_markup=get_source_keyboard(),
    )


@router.callback_query(F.data.startswith("source_"))
async def process_source_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор источников данных."""
    source = callback.data.replace("source_", "")

    use_twogis = source in ["both", "2gis"]
    use_yandex = source in ["both", "yandex"]

    # Получаем данные
    data = await state.get_data()
    query = data.get("query")

    if not query:
        await callback.answer("❌ Запрос не найден. Начните заново: /scrape")
        return

    await callback.answer("🔄 Начинаю поиск...")
    await state.set_state(ScrapperStates.scrapping)

    # Отправляем сообщение о начале
    progress_message = await callback.message.edit_text(
        f"🔍 <b>Поиск: {query}</b>\n\n"
        f"⏳ Инициализация...\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"2ГИС: {'✅' if use_twogis else '⬜'}\n"
        f"Яндекс: {'✅' if use_yandex else '⬜'}"
    )

    # Callback для обновления прогресса
    async def update_progress(status: str, current: int, total: int):
        try:
            progress_bar = "▓" * (current // 10) + "░" * (10 - current // 10)
            await progress_message.edit_text(
                f"🔍 <b>Поиск: {query}</b>\n\n"
                f"⏳ {status}\n"
                f"[{progress_bar}] {current}%\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"2ГИС: {'✅' if use_twogis else '⬜'}\n"
                f"Яндекс: {'✅' if use_yandex else '⬜'}"
            )
        except Exception:
            pass  # Игнорируем ошибки обновления

    # Запускаем скраппинг
    try:
        orchestrator = ScrapperOrchestrator(
            max_results=settings.scrapper_max_results if hasattr(settings, 'scrapper_max_results') else 100,
            use_twogis=use_twogis,
            use_yandex=use_yandex,
            headless=True,
            dadata_token=settings.dadata_token if hasattr(settings, 'dadata_token') else None,
            find_inn=True,
        )

        result = await orchestrator.scrape(query, progress_callback=update_progress)

        # Сохраняем результат
        active_tasks[callback.from_user.id] = result

        if not result.companies:
            await progress_message.edit_text(
                f"😕 <b>Компании не найдены</b>\n\n"
                f"Запрос: {query}\n\n"
                f"Попробуйте:\n"
                f"• Изменить категорию\n"
                f"• Выбрать другой город\n"
                f"• Использовать оба источника"
            )
            await state.clear()
            return

        # Показываем результат
        await progress_message.edit_text(
            f"✅ <b>Поиск завершён!</b>\n\n"
            f"📊 <b>Результаты:</b>\n"
            f"• Найдено: {result.total_found}\n"
            f"• Уникальных: {len(result.companies)}\n"
            f"• Дубликатов удалено: {result.duplicates_removed}\n"
            f"• Из 2ГИС: {result.from_twogis}\n"
            f"• Из Яндекс: {result.from_yandex}\n"
            f"• Время: {result.duration_seconds:.1f} сек\n\n"
            f"Хотите обогатить данные телефонами ЛПР?\n"
            f"Это займёт ~{len(result.companies) * 3} секунд.",
            reply_markup=get_enrichment_keyboard(),
        )

        await state.set_state(ScrapperStates.enriching)

    except Exception as e:
        logger.error(f"Scrapping error: {e}")
        await progress_message.edit_text(
            f"❌ <b>Ошибка при поиске</b>\n\n"
            f"Запрос: {query}\n"
            f"Ошибка: {str(e)}\n\n"
            f"Попробуйте позже или используйте другой запрос."
        )
        await state.clear()


@router.callback_query(F.data == "enrich_scraped")
async def enrich_scraped_companies(callback: CallbackQuery, state: FSMContext) -> None:
    """Обогащение спарсенных компаний."""
    result = active_tasks.get(callback.from_user.id)

    if not result or not result.companies:
        await callback.answer("❌ Результаты не найдены. Начните заново: /scrape")
        return

    await callback.answer("🔄 Начинаю обогащение...")

    # Создаём сообщение прогресса
    progress_message = await callback.message.edit_text(
        f"🔄 <b>Обогащение данных</b>\n\n"
        f"Компаний: {len(result.companies)}\n"
        f"Прогресс: 0/{len(result.companies)}\n\n"
        f"⏳ Получение телефонов ЛПР..."
    )

    try:
        # Конвертируем ScrapedCompany в Company для enrichment
        from bot.models.company import Company, EnrichmentStatus

        companies = []
        for sc in result.companies:
            company = Company(
                inn=sc.inn or "",
                name=sc.name,
                status=EnrichmentStatus.PENDING if sc.inn else EnrichmentStatus.INVALID_INN,
            )
            # Сохраняем дополнительные данные
            company.address = sc.address
            company.source_phone = sc.phone
            company.rating = sc.rating
            companies.append(company)

        # Запускаем обогащение
        processed = 0
        for company in companies:
            if company.inn:
                await enrich_single(company)

            processed += 1
            if processed % 5 == 0:
                try:
                    await progress_message.edit_text(
                        f"🔄 <b>Обогащение данных</b>\n\n"
                        f"Прогресс: {processed}/{len(companies)}\n"
                        f"Текущая: {company.name[:30]}...\n\n"
                        f"⏳ Получение телефонов ЛПР..."
                    )
                except Exception:
                    pass

        # Генерируем Excel
        excel_bytes = generate_excel(companies)

        # Отправляем файл
        from aiogram.types import BufferedInputFile

        filename = f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file = BufferedInputFile(excel_bytes, filename=filename)

        await callback.message.answer_document(
            file,
            caption=(
                f"✅ <b>Готово!</b>\n\n"
                f"📊 Компаний: {len(companies)}\n"
                f"📱 С телефонами ЛПР: {sum(1 for c in companies if c.phone)}\n"
                f"📍 С адресами: {sum(1 for c in companies if hasattr(c, 'address') and c.address)}"
            ),
        )

        await progress_message.delete()
        await state.clear()

        # Очищаем задачу
        del active_tasks[callback.from_user.id]

    except Exception as e:
        logger.error(f"Enrichment error: {e}")
        await progress_message.edit_text(
            f"❌ <b>Ошибка обогащения</b>\n\n"
            f"Ошибка: {str(e)}\n\n"
            f"Попробуйте скачать результаты без обогащения."
        )


@router.callback_query(F.data == "download_raw")
async def download_raw_results(callback: CallbackQuery, state: FSMContext) -> None:
    """Скачать результаты без обогащения."""
    result = active_tasks.get(callback.from_user.id)

    if not result or not result.companies:
        await callback.answer("❌ Результаты не найдены")
        return

    await callback.answer("📥 Готовлю файл...")

    try:
        # Создаём DataFrame
        import pandas as pd

        data = []
        for company in result.companies:
            data.append({
                "Название": company.name,
                "Адрес": company.address,
                "ИНН": company.inn or "",
                "Телефон (карты)": company.phone or "",
                "Рейтинг": company.rating or "",
                "Отзывов": company.reviews_count or "",
                "Категория": company.category or "",
                "Источник": company.source.value,
            })

        df = pd.DataFrame(data)

        # Создаём Excel
        from io import BytesIO
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        excel_bytes = buffer.getvalue()

        # Отправляем
        from aiogram.types import BufferedInputFile

        filename = f"companies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file = BufferedInputFile(excel_bytes, filename=filename)

        await callback.message.answer_document(
            file,
            caption=(
                f"📊 <b>Компании из поиска</b>\n\n"
                f"Всего: {len(result.companies)}\n"
                f"С ИНН: {sum(1 for c in result.companies if c.inn)}\n"
                f"С телефонами: {sum(1 for c in result.companies if c.phone)}"
            ),
        )

        await state.clear()
        del active_tasks[callback.from_user.id]

    except Exception as e:
        logger.error(f"Download error: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data == "cancel_scrape")
async def cancel_scrape(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена скраппинга."""
    await state.clear()

    if callback.from_user.id in active_tasks:
        del active_tasks[callback.from_user.id]

    await callback.message.edit_text("❌ Поиск отменён")
    await callback.answer()


def get_enrichment_keyboard():
    """Клавиатура выбора обогащения."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📱 Обогатить телефонами ЛПР",
                callback_data="enrich_scraped"
            ),
        ],
        [
            InlineKeyboardButton(
                text="📥 Скачать как есть",
                callback_data="download_raw"
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_scrape"
            ),
        ],
    ])
