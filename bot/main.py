"""Точка входа для запуска бота."""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Добавляем корневую директорию в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.utils.config import settings
from bot.handlers import start, file_upload, callbacks, scrapper

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)

# Уменьшаем уровень логов для библиотек
logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("telethon").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Главная функция запуска бота."""
    logger.info("Starting LeadPhoneFinder bot...")

    # Создаём бота с настройками по умолчанию
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Создаём диспетчер
    dp = Dispatcher()

    # Регистрируем роутеры
    dp.include_router(start.router)
    dp.include_router(file_upload.router)
    dp.include_router(callbacks.router)
    dp.include_router(scrapper.router)

    # Информация о боте
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")

    # Whitelist info
    if settings.allowed_users:
        logger.info(f"Whitelist enabled: {len(settings.allowed_users)} users")
    else:
        logger.info("Whitelist disabled: all users allowed")

    # Запускаем polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
