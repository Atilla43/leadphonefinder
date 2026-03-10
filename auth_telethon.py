"""Скрипт для авторизации Telethon-сессии.

Запустите в терминале: python auth_telethon.py
Введите SMS-код когда попросит.
После успешной авторизации файл сессии будет создан и бот сможет его использовать.
"""

import asyncio
from telethon import TelegramClient
from bot.utils.config import settings


async def main():
    if not all([settings.telethon_api_id, settings.telethon_api_hash, settings.telethon_phone]):
        print("Telethon не настроен! Укажите в .env:")
        print("  TELETHON_API_ID=...")
        print("  TELETHON_API_HASH=...")
        print("  TELETHON_PHONE=+7...")
        return

    print(f"Авторизация Telethon для номера: {settings.telethon_phone}")
    print(f"Файл сессии: {settings.telethon_session_name}.session")

    client = TelegramClient(
        settings.telethon_session_name,
        settings.telethon_api_id,
        settings.telethon_api_hash,
        lang_code="ru",
        system_lang_code="ru-RU"
    )

    await client.start(phone=settings.telethon_phone)

    me = await client.get_me()
    print(f"\nУспешно авторизован как: {me.first_name} {me.last_name or ''} (@{me.username or 'N/A'})")
    print(f"ID: {me.id}")
    print(f"\nСессия сохранена. Теперь бот сможет отправлять сообщения.")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
