"""Клавиатуры для бота."""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔍 Поиск компаний"),
                KeyboardButton(text="📄 Загрузить файл"),
            ],
            [
                KeyboardButton(text="📊 История"),
                KeyboardButton(text="❓ Помощь"),
            ],
        ],
        resize_keyboard=True,
    )


def get_scrapper_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура популярных запросов для скраппера."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🍽 Рестораны Москва",
                callback_data="query_рестораны москва"
            ),
            InlineKeyboardButton(
                text="🍽 Рестораны СПб",
                callback_data="query_рестораны санкт-петербург"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🚗 Автосервисы Москва",
                callback_data="query_автосервисы москва"
            ),
            InlineKeyboardButton(
                text="💇 Салоны Москва",
                callback_data="query_салоны красоты москва"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🏥 Стоматологии Москва",
                callback_data="query_стоматологии москва"
            ),
            InlineKeyboardButton(
                text="💪 Фитнес Москва",
                callback_data="query_фитнес москва"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🌴 Рестораны Сочи",
                callback_data="query_рестораны сочи"
            ),
            InlineKeyboardButton(
                text="🏨 Отели Сочи",
                callback_data="query_отели сочи"
            ),
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_scrape"),
        ],
    ])


def get_source_keyboard() -> InlineKeyboardMarkup:
    """Выбор источников данных."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📍 2ГИС + Яндекс (рекомендуется)",
                callback_data="source_both"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🟢 Только 2ГИС",
                callback_data="source_2gis"
            ),
            InlineKeyboardButton(
                text="🔴 Только Яндекс",
                callback_data="source_yandex"
            ),
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_scrape"),
        ],
    ])


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
        ],
    ])


def get_file_actions_keyboard() -> InlineKeyboardMarkup:
    """Действия после загрузки файла."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📱 Обогатить телефонами",
                callback_data="enrich_file"
            ),
        ],
        [
            InlineKeyboardButton(
                text="✅ Только валидация ИНН",
                callback_data="validate_only"
            ),
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
        ],
    ])


def get_enrichment_progress_keyboard(can_cancel: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура во время обогащения."""
    buttons = []

    if can_cancel:
        buttons.append([
            InlineKeyboardButton(
                text="⏸ Остановить",
                callback_data="stop_enrichment"
            ),
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_result_keyboard() -> InlineKeyboardMarkup:
    """Действия после получения результата."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📥 Скачать Excel",
                callback_data="download_excel"
            ),
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data="show_stats"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 Новый поиск",
                callback_data="new_search"
            ),
        ],
    ])
