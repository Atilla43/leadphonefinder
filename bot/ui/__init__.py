"""UI компоненты бота."""

from bot.ui.keyboards import (
    get_main_keyboard,
    get_scrapper_keyboard,
    get_source_keyboard,
    get_cancel_keyboard,
)
from bot.ui.messages import (
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    SCRAPPER_START,
    SCRAPPER_PROGRESS,
    SCRAPPER_COMPLETE,
    SCRAPPER_ERROR,
)

__all__ = [
    "get_main_keyboard",
    "get_scrapper_keyboard",
    "get_source_keyboard",
    "get_cancel_keyboard",
    "WELCOME_MESSAGE",
    "HELP_MESSAGE",
    "SCRAPPER_START",
    "SCRAPPER_PROGRESS",
    "SCRAPPER_COMPLETE",
    "SCRAPPER_ERROR",
]
