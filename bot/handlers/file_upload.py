"""Обработчик загрузки файлов."""

import asyncio
import logging
import uuid
from collections import defaultdict
from io import BytesIO
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message, BufferedInputFile

from bot.handlers.start import check_access
from bot.models.company import Company, EnrichmentResult
from bot.services.file_parser import (
    parse_file, get_file_stats, FileParseError,
    detect_outreach_file, parse_outreach_file,
)
from bot.services.enrichment import enrich_companies
from bot.services.result_generator import generate_excel, generate_csv
from bot.utils.config import settings
from bot.utils.keyboards import Keyboards
from bot.utils.messages import Messages

logger = logging.getLogger(__name__)
router = Router()

# Хранилище текущих задач обработки
# user_id -> {"companies": list, "task_id": str, "cancel_event": Event}
processing_tasks: dict[int, dict] = {}

# Локи для предотвращения race conditions (по user_id)
_user_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


@router.message(F.document)
async def handle_document(message: Message, bot: Bot) -> None:
    """Обработчик загруженных документов."""
    if not check_access(message.from_user.id):
        await message.answer(Messages.access_denied())
        return

    user_id = message.from_user.id

    # Проверяем, нет ли уже активной задачи
    async with _user_locks[user_id]:
        if user_id in processing_tasks:
            await message.answer(
                Messages.file_error("У вас уже есть файл в обработке. Дождитесь завершения."),
                reply_markup=Keyboards.back_to_menu(),
                parse_mode="HTML",
            )
            return

    document = message.document

    # Проверка расширения
    filename = document.file_name or "file"
    if not (filename.lower().endswith(".xlsx") or filename.lower().endswith(".csv")):
        await message.answer(
            Messages.file_error("Поддерживаются только файлы .xlsx и .csv"),
            reply_markup=Keyboards.back_to_menu(),
            parse_mode="HTML",
        )
        return

    # Проверка размера
    if document.file_size > settings.max_file_size_bytes:
        await message.answer(
            Messages.file_too_large(settings.max_file_size_mb),
            reply_markup=Keyboards.back_to_menu(),
            parse_mode="HTML",
        )
        return

    # Скачиваем файл с таймаутами
    try:
        file = await asyncio.wait_for(
            bot.get_file(document.file_id),
            timeout=30.0,
        )
        file_bytes = BytesIO()
        await asyncio.wait_for(
            bot.download_file(file.file_path, file_bytes),
            timeout=60.0,
        )
        file_content = file_bytes.getvalue()
    except asyncio.TimeoutError:
        logger.error("Timeout downloading file")
        await message.answer(
            Messages.file_error("Таймаут при скачивании файла. Попробуйте ещё раз."),
            reply_markup=Keyboards.back_to_menu(),
            parse_mode="HTML",
        )
        return
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        await message.answer(
            Messages.file_error("Не удалось скачать файл"),
            reply_markup=Keyboards.back_to_menu(),
            parse_mode="HTML",
        )
        return

    # Проверяем: это файл с телефонами для outreach?
    if detect_outreach_file(file_content, filename):
        try:
            recipients = parse_outreach_file(file_content, filename)
        except FileParseError as e:
            await message.answer(
                Messages.file_error(str(e)),
                reply_markup=Keyboards.back_to_menu(),
                parse_mode="HTML",
            )
            return

        # Сохраняем в results_storage для outreach
        from bot.handlers.callbacks import results_storage
        from bot.models.company import Company as CompanyModel

        # Конвертируем recipients в Company-подобные объекты для совместимости
        companies_for_storage = []
        for r in recipients:
            c = CompanyModel(inn="", name=r.company_name)
            c.phone = r.phone
            c.contact_names = [r.contact_name] if r.contact_name else []
            companies_for_storage.append(c)

        results_storage[user_id] = {"companies": companies_for_storage}

        await message.answer(
            Messages.outreach_file_received(filename, len(recipients)),
            reply_markup=Keyboards.outreach_file_result(),
            parse_mode="HTML",
        )
        return

    # Парсим файл (стандартный путь — ИНН)
    try:
        companies = parse_file(file_content, filename)
    except FileParseError as e:
        await message.answer(
            Messages.file_error(str(e)),
            reply_markup=Keyboards.back_to_menu(),
            parse_mode="HTML",
        )
        return

    # Проверка количества строк
    if len(companies) > settings.max_rows:
        await message.answer(
            Messages.too_many_rows(settings.max_rows, len(companies)),
            reply_markup=Keyboards.back_to_menu(),
            parse_mode="HTML",
        )
        return

    # Получаем статистику
    stats = get_file_stats(companies)

    # Сохраняем данные для обработки (с блокировкой)
    task_id = str(uuid.uuid4())[:8]
    async with _user_locks[user_id]:
        processing_tasks[user_id] = {
            "companies": companies,
            "task_id": task_id,
            "filename": filename,
            "cancel_event": asyncio.Event(),
        }

    await message.answer(
        Messages.file_received(filename, stats),
        reply_markup=Keyboards.confirm_processing(),
        parse_mode="HTML",
    )


async def process_companies(
    message: Message, bot: Bot, user_id: int
) -> tuple[Optional[EnrichmentResult], Optional[Message]]:
    """
    Запускает обработку компаний.

    Returns:
        (result, progress_message) - результат и сообщение с прогрессом
    """
    # Получаем данные с блокировкой
    async with _user_locks[user_id]:
        task_data = processing_tasks.get(user_id)
        if not task_data:
            return None, None
        companies = task_data["companies"]
        cancel_event = task_data["cancel_event"]

    # Отправляем сообщение о начале
    progress_message = await message.answer(
        Messages.processing_started(len(companies)),
        reply_markup=Keyboards.processing(),
        parse_mode="HTML",
    )

    # Список последних результатов для отображения
    last_results: list[Company] = []

    async def progress_callback(
        current: int, total: int, last_company: Optional[Company]
    ) -> None:
        """Callback для обновления прогресса."""
        if last_company:
            last_results.append(last_company)

        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=progress_message.message_id,
                text=Messages.processing_progress(current, total, last_results),
                reply_markup=Keyboards.processing(),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.debug(f"Failed to update progress: {e}")

    # Запускаем обогащение
    result = await enrich_companies(
        companies,
        progress_callback=progress_callback,
        cancel_event=cancel_event,
    )

    # Удаляем задачу (с блокировкой)
    async with _user_locks[user_id]:
        processing_tasks.pop(user_id, None)

    return result, progress_message


async def get_pending_companies(user_id: int) -> Optional[list[Company]]:
    """Возвращает компании, ожидающие обработки."""
    async with _user_locks[user_id]:
        task_data = processing_tasks.get(user_id)
        return task_data["companies"] if task_data else None


async def cancel_processing(user_id: int) -> bool:
    """Отменяет обработку."""
    async with _user_locks[user_id]:
        task_data = processing_tasks.get(user_id)
        if task_data:
            task_data["cancel_event"].set()
            return True
        return False


async def clear_pending(user_id: int) -> None:
    """Очищает ожидающие данные."""
    async with _user_locks[user_id]:
        processing_tasks.pop(user_id, None)
