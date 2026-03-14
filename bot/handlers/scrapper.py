"""Обработчик команд скраппера."""

import asyncio
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.services.scrapper.cache import ScrapperCache
from bot.services.scrapper.orchestrator import ScrapperOrchestrator
from bot.services.scrapper.query_parser import QueryParser
from bot.services.scrapper.models import ScrapperResult
from bot.services.enrichment import enrich_single
from bot.services.result_generator import generate_excel
from bot.utils.config import settings
from bot.utils.keyboards import Keyboards
from bot.ui.keyboards import get_scrapper_keyboard, get_source_keyboard
logger = logging.getLogger(__name__)
router = Router()


class ScrapperStates(StatesGroup):
    """Состояния FSM для скраппера."""
    waiting_query = State()
    selecting_source = State()
    scrapping = State()
    selecting_limit = State()
    enriching = State()


# Хранилище активных задач скраппинга
active_tasks: dict[int, ScrapperResult] = {}


SCRAPE_WELCOME = (
    "🔍 <b>Поиск компаний</b>\n\n"
    "Введите запрос для поиска, например:\n"
    "• <code>рестораны Сочи</code>\n"
    "• <code>автосервисы Москва</code>\n"
    "• <code>салоны красоты Казань</code>\n\n"
    "Или выберите популярный запрос:"
)


@router.callback_query(F.data == "start_scrape")
async def callback_start_scrape(callback: CallbackQuery, state: FSMContext) -> None:
    """Кнопка 'Поиск компаний' из главного меню."""
    if settings.allowed_users and callback.from_user.id not in settings.allowed_users:
        await callback.answer("⛔ У вас нет доступа к этой функции.", show_alert=True)
        return

    await state.set_state(ScrapperStates.waiting_query)
    await callback.message.edit_text(
        SCRAPE_WELCOME,
        reply_markup=get_scrapper_keyboard(),
    )
    await callback.answer()


@router.message(Command("scrape"))
async def cmd_scrape(message: Message, state: FSMContext) -> None:
    """Команда /scrape - начало скраппинга."""
    if settings.allowed_users and message.from_user.id not in settings.allowed_users:
        await message.answer("⛔ У вас нет доступа к этой функции.")
        return

    await state.set_state(ScrapperStates.waiting_query)
    await message.answer(SCRAPE_WELCOME, reply_markup=get_scrapper_keyboard())


@router.callback_query(F.data.startswith("query_"))
async def process_quick_query(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка быстрого запроса из кнопки."""
    query = callback.data.replace("query_", "")
    await callback.answer()

    # Создаём фейковое сообщение — просто переиспользуем логику
    parser = QueryParser()
    parsed = parser.parse(query)

    if not parsed.is_valid:
        await callback.message.edit_text(
            f"❌ Не удалось разобрать запрос: {query}\n"
            "Попробуйте ввести вручную."
        )
        return

    await state.update_data(query=query, parsed=parsed)
    await state.set_state(ScrapperStates.selecting_source)

    response_lines = [
        f"📍 <b>Запрос:</b> {query}",
        f"📂 <b>Категория:</b> {parsed.category}",
        f"🏙 <b>Город:</b> {parsed.location}",
        "",
        "Выберите источники данных:",
    ]

    await callback.message.edit_text(
        "\n".join(response_lines),
        reply_markup=get_source_keyboard(),
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
        cache = ScrapperCache(
            cache_dir=settings.scrapper_cache_dir,
            ttl_hours=settings.scrapper_cache_ttl_hours,
        )

        orchestrator = ScrapperOrchestrator(
            max_results=settings.scrapper_max_results if hasattr(settings, 'scrapper_max_results') else 100,
            use_twogis=use_twogis,
            use_yandex=use_yandex,
            headless=True,
            dadata_token=settings.dadata_token if hasattr(settings, 'dadata_token') else None,
            find_inn=True,
            cache=cache,
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
        if result.from_cache and result.cached_at:
            from datetime import datetime as dt
            age = dt.now() - result.cached_at
            hours = int(age.total_seconds() // 3600)
            minutes = int((age.total_seconds() % 3600) // 60)
            age_str = f"{hours}ч {minutes}мин" if hours else f"{minutes}мин"
            header = f"✅ <b>Поиск завершён!</b> (из кеша, {age_str} назад)"
            time_line = f"• ⏱ Кешировано: {age_str} назад"
        else:
            header = "✅ <b>Поиск завершён!</b>"
            time_line = f"• Время: {result.duration_seconds:.1f} сек"

        await progress_message.edit_text(
            f"{header}\n\n"
            f"📊 <b>Результаты:</b>\n"
            f"• Найдено: {result.total_found}\n"
            f"• Уникальных: {len(result.companies)}\n"
            f"• Дубликатов удалено: {result.duplicates_removed}\n"
            f"• Из 2ГИС: {result.from_twogis}\n"
            f"• Из Яндекс: {result.from_yandex}\n"
            f"{time_line}\n\n"
            f"Хотите обогатить данные телефонами ЛПР?\n"
            f"Выберите количество пробивов:",
            reply_markup=Keyboards.enrichment_limit(),
        )

        await state.set_state(ScrapperStates.selecting_limit)

    except Exception as e:
        logger.error(f"Scrapping error: {e}")
        await progress_message.edit_text(
            f"❌ <b>Ошибка при поиске</b>\n\n"
            f"Запрос: {query}\n"
            f"Ошибка: {str(e)}\n\n"
            f"Попробуйте позже или используйте другой запрос."
        )
        await state.clear()


@router.callback_query(F.data.startswith("enrich_limit:"))
async def enrich_with_limit(callback: CallbackQuery, state: FSMContext) -> None:
    """Обогащение спарсенных компаний с выбранным лимитом."""
    limit_str = callback.data.split(":")[1]

    # Пропустить обогащение — скачать как есть
    if limit_str == "skip":
        await download_raw_results(callback, state)
        return

    result = active_tasks.get(callback.from_user.id)
    if not result or not result.companies:
        await callback.answer("❌ Результаты не найдены. Начните заново: /scrape")
        return

    limit = int(limit_str)  # 0 = все

    await callback.answer("🔄 Начинаю обогащение...")
    await state.set_state(ScrapperStates.enriching)

    # Конвертируем ScrapedCompany в Company
    from bot.models.company import Company, EnrichmentStatus

    companies = []
    for sc in result.companies:
        company = Company(
            inn=sc.inn or "",
            name=sc.name,
            status=EnrichmentStatus.PENDING if sc.inn else EnrichmentStatus.INVALID_INN,
            director_name=sc.director_name,
            map_phone=sc.phone,
            website=sc.website,
            category=sc.category,
            rating=sc.rating,
            reviews_count=sc.reviews_count,
            working_hours=sc.working_hours,
            latitude=sc.latitude,
            longitude=sc.longitude,
            legal_form=sc.legal_form,
            legal_name=sc.legal_name,
            addresses=[sc.address] if sc.address else [],
        )
        companies.append(company)

    # Определяем сколько обогащать
    companies_with_inn = [c for c in companies if c.inn]
    to_enrich = companies_with_inn[:limit] if limit > 0 else companies_with_inn
    enrich_count = len(to_enrich)

    progress_message = await callback.message.edit_text(
        f"🔄 <b>Обогащение данных</b>\n\n"
        f"Всего компаний: {len(companies)}\n"
        f"К обогащению: {enrich_count}\n"
        f"Прогресс: 0/{enrich_count}\n\n"
        f"⏳ Получение телефонов ЛПР..."
    )

    try:
        processed = 0
        for company in to_enrich:
            await enrich_single(company)
            processed += 1

            if processed % 5 == 0 or processed == enrich_count:
                try:
                    pct = int(processed / enrich_count * 100)
                    bar = "▓" * (pct // 10) + "░" * (10 - pct // 10)
                    await progress_message.edit_text(
                        f"🔄 <b>Обогащение данных</b>\n\n"
                        f"[{bar}] {pct}%\n"
                        f"Прогресс: {processed}/{enrich_count}\n"
                        f"Текущая: {company.name[:30]}\n\n"
                        f"⏳ Получение телефонов ЛПР..."
                    )
                except Exception:
                    pass

        # Генерируем Excel
        excel_bytes, excel_filename = generate_excel(companies, "leads")

        from aiogram.types import BufferedInputFile

        file = BufferedInputFile(excel_bytes, filename=excel_filename)

        found_phones = sum(1 for c in companies if c.phone)
        found_emails = sum(1 for c in companies if c.emails)

        # Сохраняем результаты для outreach
        from bot.handlers.callbacks import results_storage
        results_storage[callback.from_user.id] = {
            "companies": companies,
        }

        await callback.message.answer_document(
            file,
            caption=(
                f"✅ <b>Готово!</b>\n\n"
                f"📊 Компаний: {len(companies)}\n"
                f"🔍 Обогащено: {enrich_count}\n"
                f"📱 С телефонами: {found_phones}\n"
                f"📧 С email: {found_emails}"
            ),
            reply_markup=Keyboards.result(),
        )

        await progress_message.delete()
        await state.clear()
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
                "Сайт": company.website or "",
                "Категория": company.category or "",
                "Рейтинг": company.rating or "",
                "Отзывов": company.reviews_count or "",
                "Время работы": company.working_hours or "",
                "Директор": company.director_name or "",
                "Форма юр лица": company.legal_form or "",
                "Юр название": company.legal_name or "",
                "Широта": company.latitude or "",
                "Долгота": company.longitude or "",
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


