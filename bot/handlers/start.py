"""Обработчики команд /start и /help."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from bot.utils.config import settings
from bot.utils.keyboards import Keyboards
from bot.utils.messages import Messages

router = Router()


def check_access(user_id: int) -> bool:
    """Проверяет доступ пользователя."""
    allowed = settings.allowed_users
    # Если whitelist пустой, разрешаем всем
    if not allowed:
        return True
    return user_id in allowed


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start."""
    if not check_access(message.from_user.id):
        await message.answer(Messages.access_denied())
        return

    await message.answer(
        Messages.welcome(),
        reply_markup=Keyboards.main_menu(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help."""
    if not check_access(message.from_user.id):
        await message.answer(Messages.access_denied())
        return

    await message.answer(
        Messages.help_text(),
        reply_markup=Keyboards.back_to_menu(),
        parse_mode="HTML",
    )
