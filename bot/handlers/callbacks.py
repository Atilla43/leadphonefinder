"""Обработчики callback-кнопок."""

import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, BufferedInputFile

from bot.handlers.start import check_access
from bot.handlers.file_upload import (
    process_companies,
    get_pending_companies,
    cancel_processing,
    clear_pending,
)
from bot.services.result_generator import (
    generate_excel,
    generate_csv,
    generate_template_excel,
    generate_template_csv,
)
from bot.utils.keyboards import Keyboards
from bot.utils.messages import Messages

logger = logging.getLogger(__name__)
router = Router()

# Хранилище результатов для скачивания
# user_id -> EnrichmentResult
results_storage: dict[int, dict] = {}


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery) -> None:
    """Возврат в главное меню."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    await clear_pending(callback.from_user.id)
    await callback.message.edit_text(
        Messages.welcome(),
        reply_markup=Keyboards.main_menu(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "template")
async def callback_template(callback: CallbackQuery) -> None:
    """Выбор формата шаблона."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    await callback.message.edit_text(
        "📥 <b>Скачать шаблон</b>\n\nВыбери формат файла:",
        reply_markup=Keyboards.template_format(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "template_xlsx")
async def callback_template_xlsx(callback: CallbackQuery, bot: Bot) -> None:
    """Отправка шаблона Excel."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    content, filename = generate_template_excel()
    file = BufferedInputFile(content, filename=filename)

    await bot.send_document(
        chat_id=callback.message.chat.id,
        document=file,
        caption="📊 Шаблон файла Excel\n\nЗаполни колонки «ИНН» и «Название», затем загрузи файл.",
    )
    await callback.answer("Шаблон отправлен")


@router.callback_query(F.data == "template_csv")
async def callback_template_csv(callback: CallbackQuery, bot: Bot) -> None:
    """Отправка шаблона CSV."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    content, filename = generate_template_csv()
    file = BufferedInputFile(content, filename=filename)

    await bot.send_document(
        chat_id=callback.message.chat.id,
        document=file,
        caption="📄 Шаблон файла CSV\n\nЗаполни колонки «ИНН» и «Название», затем загрузи файл.",
    )
    await callback.answer("Шаблон отправлен")


@router.callback_query(F.data == "upload_hint")
async def callback_upload_hint(callback: CallbackQuery) -> None:
    """Подсказка для загрузки."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    await callback.message.edit_text(
        Messages.upload_hint(),
        reply_markup=Keyboards.back_to_menu(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery) -> None:
    """Помощь."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    await callback.message.edit_text(
        Messages.help_text(),
        reply_markup=Keyboards.back_to_menu(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "start_process")
async def callback_start_process(callback: CallbackQuery, bot: Bot) -> None:
    """Начать обработку файла."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    user_id = callback.from_user.id
    companies = await get_pending_companies(user_id)

    if not companies:
        await callback.answer("Нет данных для обработки", show_alert=True)
        return

    await callback.answer("Обработка запущена...")

    # Удаляем сообщение с подтверждением
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Запускаем обработку
    result, progress_message = await process_companies(callback.message, bot, user_id)

    if result and progress_message:
        # Сохраняем результат
        results_storage[user_id] = {
            "result": result,
            "companies": result.companies,
        }

        # Обновляем сообщение с прогрессом на результат
        try:
            await progress_message.edit_text(
                Messages.processing_complete(result),
                reply_markup=Keyboards.result(),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to update result message: {e}")
            # Fallback: отправляем новое сообщение
            await callback.message.answer(
                Messages.processing_complete(result),
                reply_markup=Keyboards.result(),
                parse_mode="HTML",
            )
    elif progress_message:
        await progress_message.edit_text(
            Messages.processing_cancelled(),
            reply_markup=Keyboards.back_to_menu(),
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(
            Messages.processing_cancelled(),
            reply_markup=Keyboards.back_to_menu(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "cancel_upload")
async def callback_cancel_upload(callback: CallbackQuery) -> None:
    """Отмена загрузки."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    await clear_pending(callback.from_user.id)
    await callback.message.edit_text(
        Messages.welcome(),
        reply_markup=Keyboards.main_menu(),
        parse_mode="HTML",
    )
    await callback.answer("Отменено")


@router.callback_query(F.data == "cancel_process")
async def callback_cancel_process(callback: CallbackQuery) -> None:
    """Отмена обработки."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    if await cancel_processing(callback.from_user.id):
        await callback.answer("Отмена обработки...")
    else:
        await callback.answer("Нет активной обработки")


@router.callback_query(F.data == "download_xlsx")
async def callback_download_xlsx(callback: CallbackQuery, bot: Bot) -> None:
    """Скачать результат в Excel."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    user_data = results_storage.get(callback.from_user.id)
    if not user_data:
        await callback.answer("Нет результатов для скачивания", show_alert=True)
        return

    companies = user_data["companies"]
    content, filename = generate_excel(companies)
    file = BufferedInputFile(content, filename=filename)

    await bot.send_document(
        chat_id=callback.message.chat.id,
        document=file,
        caption="📊 Результат обработки (Excel)",
    )
    await callback.answer("Файл отправлен")


@router.callback_query(F.data == "download_csv")
async def callback_download_csv(callback: CallbackQuery, bot: Bot) -> None:
    """Скачать результат в CSV."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    user_data = results_storage.get(callback.from_user.id)
    if not user_data:
        await callback.answer("Нет результатов для скачивания", show_alert=True)
        return

    companies = user_data["companies"]
    content, filename = generate_csv(companies)
    file = BufferedInputFile(content, filename=filename)

    await bot.send_document(
        chat_id=callback.message.chat.id,
        document=file,
        caption="📄 Результат обработки (CSV)",
    )
    await callback.answer("Файл отправлен")


@router.callback_query(F.data == "history")
async def callback_history(callback: CallbackQuery) -> None:
    """История загрузок."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    # Пока просто показываем сообщение о пустой истории
    # В будущем можно добавить хранение истории в БД
    await callback.message.edit_text(
        Messages.no_history(),
        reply_markup=Keyboards.back_to_menu(),
        parse_mode="HTML",
    )
    await callback.answer()
