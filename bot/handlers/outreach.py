"""Обработчики AI-продажника (outreach)."""

import asyncio
import logging
from io import BytesIO

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message, BufferedInputFile

from bot.handlers.callbacks import results_storage
from bot.handlers.start import check_access
from bot.models.outreach import OutreachCampaign, OutreachRecipient
from bot.services.ai_sales import AISalesEngine
from bot.services.file_parser import parse_outreach_file, FileParseError
from bot.services.outreach import OutreachService, active_outreach
from bot.services.result_generator import generate_outreach_template
from bot.utils.config import settings
from bot.utils.keyboards import Keyboards
from bot.utils.messages import Messages

logger = logging.getLogger(__name__)
router = Router()


class OutreachStates(StatesGroup):
    waiting_file = State()
    waiting_dialog_limit = State()
    waiting_offer = State()
    confirming = State()
    waiting_managers = State()
    sending = State()
    listening = State()


def _get_recipients_from_results(user_id: int) -> list[OutreachRecipient]:
    """Извлекает получателей из результатов обогащения."""
    user_data = results_storage.get(user_id)
    if not user_data:
        return []

    companies = user_data.get("companies", [])
    recipients = []

    for company in companies:
        phone = getattr(company, "phone", None) or ""
        if not phone:
            continue

        # Берём первый телефон если несколько
        first_phone = phone.split(",")[0].strip()
        if not first_phone:
            continue

        contact_name = None
        names = getattr(company, "contact_names", [])
        if names:
            contact_name = names[0]

        recipients.append(OutreachRecipient(
            phone=first_phone,
            company_name=company.name,
            contact_name=contact_name,
            category=getattr(company, "category", None),
            rating=getattr(company, "rating", None),
            reviews_count=getattr(company, "reviews_count", None),
            website=getattr(company, "website", None),
            working_hours=getattr(company, "working_hours", None),
            address=company.addresses[0] if getattr(company, "addresses", None) else None,
            director_name=getattr(company, "director_name", None),
        ))

    return recipients


def _check_outreach_config(callback: CallbackQuery) -> str | None:
    """Проверяет конфигурацию для outreach. Возвращает текст ошибки или None."""
    if not settings.openrouter_api_key:
        return "OpenRouter API ключ не настроен (OPENROUTER_API_KEY в .env)"
    if not all([settings.telethon_api_id, settings.telethon_api_hash, settings.telethon_phone]):
        return "Telethon не настроен (TELETHON_API_ID/HASH/PHONE в .env)"
    return None


@router.callback_query(F.data == "outreach_menu")
async def outreach_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Меню AI-продажника — выбор источника контактов."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    error = _check_outreach_config(callback)
    if error:
        await callback.answer(error, show_alert=True)
        return

    has_campaign = callback.from_user.id in active_outreach
    await callback.message.edit_text(
        Messages.outreach_menu(),
        reply_markup=Keyboards.outreach_source(has_campaign=has_campaign),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "outreach_upload")
async def outreach_upload(callback: CallbackQuery, state: FSMContext) -> None:
    """Загрузка файла с контактами — отправляем шаблон и ждём файл."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    # Генерируем и отправляем шаблон
    template_bytes, template_name = generate_outreach_template()

    await callback.message.edit_text(
        Messages.outreach_upload_hint(),
        reply_markup=Keyboards.back_to_menu(),
        parse_mode="HTML",
    )

    await callback.message.answer_document(
        BufferedInputFile(template_bytes, filename=template_name),
        caption="📋 Шаблон для AI-Продажника. Заполните и отправьте обратно.",
    )

    await state.set_state(OutreachStates.waiting_file)
    await callback.answer()


@router.message(OutreachStates.waiting_file, F.text)
async def waiting_file_text(message: Message, state: FSMContext) -> None:
    """Пользователь отправил текст вместо файла."""
    await message.answer("Отправьте файл Excel (.xlsx) с контактами, а не текст.")


@router.message(OutreachStates.waiting_file, F.document)
async def receive_outreach_file(message: Message, bot: Bot, state: FSMContext) -> None:
    """Получение файла с контактами для outreach."""
    if not check_access(message.from_user.id):
        return

    document = message.document
    filename = document.file_name or "file"

    if not filename.lower().endswith((".xlsx", ".xls", ".csv")):
        await message.answer(
            "Поддерживаются только файлы .xlsx и .csv. Попробуйте ещё раз.",
            parse_mode="HTML",
        )
        return

    # Скачиваем
    try:
        file = await bot.get_file(document.file_id)
        file_bytes = BytesIO()
        await bot.download_file(file.file_path, file_bytes)
        file_content = file_bytes.getvalue()
    except Exception as e:
        logger.error(f"Error downloading outreach file: {e}")
        await message.answer(
            "Не удалось скачать файл. Попробуйте ещё раз.",
            reply_markup=Keyboards.back_to_menu(),
        )
        return

    # Парсим
    try:
        recipients = parse_outreach_file(file_content, filename)
    except FileParseError as e:
        await message.answer(
            f"Ошибка: {e}\n\nУбедитесь, что файл содержит колонку «Телефон» и «Компания».",
            reply_markup=Keyboards.back_to_menu(),
            parse_mode="HTML",
        )
        return

    # Сохраняем в FSM (все поля для AI контекста)
    await state.update_data(recipients=[
        {
            "phone": r.phone,
            "company_name": r.company_name,
            "contact_name": r.contact_name,
            "category": r.category,
            "rating": r.rating,
            "reviews_count": r.reviews_count,
            "website": r.website,
            "working_hours": r.working_hours,
            "address": r.address,
            "director_name": r.director_name,
        }
        for r in recipients
    ])
    await state.set_state(OutreachStates.waiting_dialog_limit)

    await message.answer(
        Messages.outreach_dialog_limit(len(recipients)),
        reply_markup=Keyboards.outreach_dialog_limit(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("outreach_limit:"), OutreachStates.waiting_dialog_limit)
async def select_dialog_limit(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор количества AI-диалогов."""
    limit = int(callback.data.split(":")[1])

    data = await state.get_data()
    recipients = data["recipients"]

    # Применяем лимит (0 = все)
    if limit > 0 and len(recipients) > limit:
        recipients = recipients[:limit]
        await state.update_data(recipients=recipients)

    await state.set_state(OutreachStates.waiting_offer)

    count = len(recipients)
    await callback.message.edit_text(
        Messages.outreach_prompt(count),
        parse_mode="HTML",
    )
    await callback.answer(f"Выбрано {count} контактов" if limit > 0 else f"Все {count} контактов")


@router.callback_query(F.data == "start_outreach")
async def start_outreach(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало AI-продажника из результатов поиска."""
    if not check_access(callback.from_user.id):
        await callback.answer(Messages.access_denied(), show_alert=True)
        return

    error = _check_outreach_config(callback)
    if error:
        await callback.answer(error, show_alert=True)
        return

    # Извлекаем получателей
    recipients = _get_recipients_from_results(callback.from_user.id)
    if not recipients:
        await callback.answer(
            "Нет контактов с телефонами для рассылки. Сначала найдите компании через поиск.",
            show_alert=True,
        )
        return

    # Сохраняем в FSM (все поля для AI контекста)
    await state.update_data(recipients=[
        {
            "phone": r.phone,
            "company_name": r.company_name,
            "contact_name": r.contact_name,
            "category": r.category,
            "rating": r.rating,
            "reviews_count": r.reviews_count,
            "website": r.website,
            "working_hours": r.working_hours,
            "address": r.address,
            "director_name": r.director_name,
        }
        for r in recipients
    ])
    await state.set_state(OutreachStates.waiting_dialog_limit)

    await callback.message.edit_text(
        Messages.outreach_dialog_limit(len(recipients)),
        reply_markup=Keyboards.outreach_dialog_limit(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(OutreachStates.waiting_offer)
async def receive_offer(message: Message, state: FSMContext) -> None:
    """Получение текста оффера."""
    if not check_access(message.from_user.id):
        return

    offer = message.text.strip()
    if not offer:
        await message.answer("Введите текст оффера.")
        return

    await state.update_data(offer=offer)
    await state.set_state(OutreachStates.confirming)

    data = await state.get_data()
    recipients = data["recipients"]

    # Берём первого получателя для превью
    sample = recipients[0]
    name = sample.get("contact_name") or "коллега"
    company = sample["company_name"]

    await message.answer(
        Messages.outreach_preview(offer, name, company, len(recipients)),
        reply_markup=Keyboards.outreach_confirm(len(recipients)),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "outreach_edit", OutreachStates.confirming)
async def edit_offer(callback: CallbackQuery, state: FSMContext) -> None:
    """Изменить оффер."""
    await state.set_state(OutreachStates.waiting_offer)

    data = await state.get_data()
    recipients = data["recipients"]

    await callback.message.edit_text(
        Messages.outreach_prompt(len(recipients)),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "outreach_cancel")
async def cancel_outreach(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена outreach."""
    await state.clear()
    await callback.message.edit_text(
        Messages.welcome(),
        reply_markup=Keyboards.main_menu(),
        parse_mode="HTML",
    )
    await callback.answer("Отменено")


@router.callback_query(F.data == "outreach_confirm", OutreachStates.confirming)
async def confirm_outreach(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение оффера — переход к настройке менеджеров."""
    await state.set_state(OutreachStates.waiting_managers)

    await callback.message.edit_text(
        Messages.outreach_managers_prompt(),
        reply_markup=Keyboards.outreach_skip_managers(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "outreach_skip_managers", OutreachStates.waiting_managers)
async def skip_managers(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Пропустить добавление менеджеров — запуск кампании."""
    await state.update_data(manager_ids=[])
    await callback.answer()
    await _launch_campaign(callback.from_user.id, state, bot, callback.message)


@router.message(OutreachStates.waiting_managers, F.text)
async def receive_managers(message: Message, state: FSMContext, bot: Bot) -> None:
    """Получение Telegram ID менеджеров."""
    text = message.text.strip()
    manager_ids = []
    errors = []

    for part in text.replace(" ", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            manager_id = int(part)
            manager_ids.append(manager_id)
        except ValueError:
            errors.append(part)

    if errors:
        await message.answer(
            f"Некорректные ID: {', '.join(errors)}\n\n"
            "Отправьте числовые Telegram ID через запятую.",
        )
        return

    if not manager_ids:
        await message.answer("Отправьте хотя бы один Telegram ID или нажмите «Пропустить».")
        return

    await state.update_data(manager_ids=manager_ids)
    await _launch_campaign(message.from_user.id, state, bot, message)


async def _launch_campaign(
    user_id: int,
    state: FSMContext,
    bot: Bot,
    source_message: Message,
) -> None:
    """Запуск кампании (общая логика для skip/receive managers)."""
    data = await state.get_data()

    # Создаём получателей (с контекстом для AI)
    recipients = [
        OutreachRecipient(
            phone=r["phone"],
            company_name=r["company_name"],
            contact_name=r.get("contact_name"),
            category=r.get("category"),
            rating=r.get("rating"),
            reviews_count=r.get("reviews_count"),
            website=r.get("website"),
            working_hours=r.get("working_hours"),
            address=r.get("address"),
            director_name=r.get("director_name"),
        )
        for r in data["recipients"]
    ]

    manager_ids = data.get("manager_ids", [])

    # Создаём кампанию
    campaign = OutreachCampaign(
        user_id=user_id,
        offer=data["offer"],
        recipients=recipients,
        manager_ids=manager_ids,
    )

    # Создаём AI engine
    ai_engine = AISalesEngine(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        model=settings.openrouter_model,
    )

    # Создаём сервис
    service = OutreachService(ai_engine)
    active_outreach[user_id] = service

    await state.set_state(OutreachStates.sending)

    # Сообщение с прогрессом
    progress_msg = await source_message.answer(
        Messages.outreach_progress(0, len(recipients), campaign),
        reply_markup=Keyboards.outreach_sending(),
        parse_mode="HTML",
    )

    # Callback для прогресса
    async def on_progress(sent: int, total: int, camp: OutreachCampaign):
        try:
            await progress_msg.edit_text(
                Messages.outreach_progress(sent, total, camp),
                reply_markup=Keyboards.outreach_sending(),
                parse_mode="HTML",
            )
        except Exception:
            pass

    # Callback для уведомлений
    async def on_notify(event_type: str, **kwargs):
        try:
            if event_type in ("warm_lead", "warm_lead_reply"):
                recipient = kwargs["recipient"]
                camp = kwargs["campaign"]
                msg_text = Messages.outreach_warm_lead(recipient)

                # Владельцу кампании
                await bot.send_message(user_id, msg_text, parse_mode="HTML")

                # Всем менеджерам
                for manager_id in camp.manager_ids:
                    try:
                        await bot.send_message(manager_id, msg_text, parse_mode="HTML")
                    except Exception as e:
                        logger.warning(f"Can't notify manager {manager_id}: {e}")

            elif event_type == "sending_complete":
                camp = kwargs["campaign"]
                managers_text = ""
                if camp.manager_ids:
                    managers_text = f"\n👥 Менеджеров на уведомлениях: {len(camp.manager_ids)}"
                await progress_msg.edit_text(
                    f"✅ <b>Рассылка завершена!</b>\n\n"
                    f"Отправлено: {camp.sent_count}\n"
                    f"Нет в Telegram: {camp.not_found_count}\n"
                    f"{managers_text}\n"
                    "AI слушает ответы и будет пинговать при игноре.",
                    reply_markup=Keyboards.outreach_listening(),
                    parse_mode="HTML",
                )
                await state.set_state(OutreachStates.listening)
            elif event_type == "daily_limit":
                await bot.send_message(
                    user_id,
                    "⚠️ Достигнут дневной лимит рассылки. Кампания продолжится завтра.",
                    parse_mode="HTML",
                )
            elif event_type == "flood_wait":
                seconds = kwargs.get("seconds", 0)
                await bot.send_message(
                    user_id,
                    f"⚠️ Telegram rate limit. Пауза {seconds} сек...",
                    parse_mode="HTML",
                )
        except Exception as e:
            logger.error(f"Notify error: {e}")

    service.set_notify_callback(on_notify)

    # Запускаем в фоне
    asyncio.create_task(service.start_campaign(campaign, on_progress))


@router.callback_query(F.data == "outreach_pause")
async def pause_outreach(callback: CallbackQuery) -> None:
    """Пауза кампании."""
    user_id = callback.from_user.id
    service = active_outreach.get(user_id)

    if not service:
        await callback.answer("Нет активной кампании", show_alert=True)
        return

    service.pause()

    await callback.message.edit_reply_markup(
        reply_markup=Keyboards.outreach_paused(),
    )
    await callback.answer("Кампания на паузе")


@router.callback_query(F.data == "outreach_resume")
async def resume_outreach(callback: CallbackQuery) -> None:
    """Возобновление кампании."""
    user_id = callback.from_user.id
    service = active_outreach.get(user_id)

    if not service:
        await callback.answer("Нет активной кампании", show_alert=True)
        return

    service.resume()

    await callback.message.edit_reply_markup(
        reply_markup=Keyboards.outreach_sending(),
    )
    await callback.answer("Кампания возобновлена")


@router.callback_query(F.data == "outreach_stop")
async def stop_outreach(callback: CallbackQuery, state: FSMContext) -> None:
    """Остановка кампании."""
    user_id = callback.from_user.id
    service = active_outreach.get(user_id)

    if not service:
        await callback.answer("Нет активной кампании", show_alert=True)
        return

    await service.cancel()
    campaign = service.campaign

    # Очищаем
    active_outreach.pop(user_id, None)
    await state.clear()

    if campaign:
        await callback.message.edit_text(
            Messages.outreach_complete(campaign),
            reply_markup=Keyboards.back_to_menu(),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "⏹ Кампания остановлена.",
            reply_markup=Keyboards.back_to_menu(),
            parse_mode="HTML",
        )

    await callback.answer("Кампания остановлена")


@router.callback_query(F.data == "outreach_status")
async def outreach_status(callback: CallbackQuery) -> None:
    """Статус кампании."""
    user_id = callback.from_user.id
    service = active_outreach.get(user_id)

    if not service or not service.campaign:
        await callback.answer("Нет активной кампании", show_alert=True)
        return

    await callback.answer()

    await callback.message.edit_text(
        Messages.outreach_status(service.campaign),
        reply_markup=Keyboards.outreach_listening(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "outreach_dialogs")
async def outreach_dialogs(callback: CallbackQuery) -> None:
    """Список диалогов кампании."""
    user_id = callback.from_user.id
    service = active_outreach.get(user_id)

    if not service or not service.campaign:
        await callback.answer("Нет активной кампании", show_alert=True)
        return

    await callback.answer()

    await callback.message.edit_text(
        Messages.outreach_dialogs_list(service.campaign),
        reply_markup=Keyboards.outreach_dialogs_back(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("dial_filter:"))
async def dialogs_filter(callback: CallbackQuery) -> None:
    """Фильтрация диалогов по статусу."""
    user_id = callback.from_user.id
    service = active_outreach.get(user_id)

    if not service or not service.campaign:
        await callback.answer("Нет активной кампании", show_alert=True)
        return

    filter_status = callback.data.split(":")[1]
    if filter_status == "all":
        filter_status = None

    await callback.answer()

    try:
        await callback.message.edit_text(
            Messages.outreach_dialogs_list(service.campaign, filter_status=filter_status),
            reply_markup=Keyboards.outreach_dialogs_back(),
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
