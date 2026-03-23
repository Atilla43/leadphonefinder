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
from bot.handlers import start, file_upload, callbacks, scrapper, outreach
from bot.services.outreach_storage import OutreachStorage
from bot.services.outreach import OutreachService, active_outreach, add_service, normalize_phone
from bot.services.ai_sales import AISalesEngine
from bot.utils.messages import Messages
from bot.services.account_pool import get_account_pool
from bot.services.sherlock_client import get_sherlock_client, is_telethon_configured

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot_live.log", encoding="utf-8"),
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
    dp.include_router(outreach.router)

    # Информация о боте
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")

    # Whitelist info
    if settings.allowed_users:
        logger.info(f"Whitelist enabled: {len(settings.allowed_users)} users")
    else:
        logger.info("Whitelist disabled: all users allowed")

    # Восстанавливаем активные кампании после перезапуска
    async def on_startup(bot: Bot) -> None:
        # Инициализируем пул аккаунтов
        pool = get_account_pool()
        connected = await pool.connect_all()
        logger.info(f"Account pool: {connected} account(s) connected")

        storage = OutreachStorage()
        campaigns = storage.load_all_active()

        # Восстанавливаем sent_today из данных кампаний
        from datetime import datetime, timezone
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        for campaign in campaigns:
            for r in campaign.recipients:
                if r.account_phone and r.last_message_at and r.status not in ("pending", "not_found"):
                    if r.last_message_at >= today_start:
                        pool.sent_today[r.account_phone] = pool.sent_today.get(r.account_phone, 0) + 1
        if pool.sent_today:
            logger.info(f"Restored sent_today counters: {dict(pool.sent_today)}")

        for campaign in campaigns:
            ai_engine = AISalesEngine(
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                model=settings.openrouter_model,
            )
            service = OutreachService(ai_engine)
            service._campaign = campaign
            add_service(campaign.user_id, campaign.campaign_id, service)

            # Устанавливаем notify callback для уведомлений после рестарта
            def _make_notify(uid, camp):
                async def on_notify(event_type: str, **kwargs):
                    try:
                        if event_type == "first_reply":
                            recipient = kwargs["recipient"]
                            msg_text = Messages.outreach_first_reply(recipient, kwargs.get("lead_message", ""))
                            await bot.send_message(uid, msg_text, parse_mode="HTML")
                            for manager_id in camp.manager_ids:
                                try:
                                    await bot.send_message(manager_id, msg_text, parse_mode="HTML")
                                except Exception:
                                    pass
                        elif event_type in ("warm_lead", "warm_lead_reply"):
                            recipient = kwargs["recipient"]
                            msg_text = Messages.outreach_warm_lead(recipient)
                            await bot.send_message(uid, msg_text, parse_mode="HTML")
                            for manager_id in camp.manager_ids:
                                try:
                                    await bot.send_message(manager_id, msg_text, parse_mode="HTML")
                                except Exception:
                                    pass
                        elif event_type == "referral":
                            recipient = kwargs["recipient"]
                            msg_text = Messages.outreach_referral(
                                recipient,
                                referral_name=kwargs.get("referral_name"),
                                referral_phone=kwargs.get("referral_phone"),
                                referral_found=kwargs.get("referral_found"),
                            )
                            await bot.send_message(uid, msg_text, parse_mode="HTML")
                            for manager_id in camp.manager_ids:
                                try:
                                    await bot.send_message(manager_id, msg_text, parse_mode="HTML")
                                except Exception:
                                    pass
                        elif event_type == "flood_wait":
                            seconds = kwargs.get("seconds", 0)
                            await bot.send_message(uid, f"⚠️ Telegram rate limit. Пауза {seconds} сек...", parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"Restored notify error: {e}")
                return on_notify

            service.set_notify_callback(_make_notify(campaign.user_id, campaign))

            if campaign.status == "paused":
                service._pause_event.clear()

            # Resolve telegram_user_id для получателей без него
            if pool.get_active_accounts():
                try:
                    from telethon.tl.functions.contacts import ImportContactsRequest
                    from telethon.tl.types import InputPhoneContact
                    resolved = 0
                    for r in campaign.recipients:
                        if r.status in ("sent", "talking") and not r.telegram_user_id:
                            # Используем клиент с которого было отправлено
                            client = None
                            if r.account_phone:
                                client = pool.get_client(r.account_phone)
                            if not client:
                                clients = pool.get_all_clients()
                                client = clients[0] if clients else None
                            if not client:
                                continue

                            phone = normalize_phone(r.phone)
                            contact = InputPhoneContact(
                                client_id=0, phone=phone,
                                first_name=r.company_name, last_name="",
                            )
                            result = await client(ImportContactsRequest([contact]))
                            if result.users:
                                r.telegram_user_id = result.users[0].id
                                resolved += 1
                    if resolved:
                        storage.save(campaign)
                        logger.info(f"Resolved {resolved} telegram_user_ids for campaign {campaign.user_id}")
                except Exception as e:
                    logger.warning(f"Failed to resolve user IDs: {e}")

            await service.start_listener()
            service._ping_task = asyncio.create_task(service._ping_loop())

            # Ответить неотвеченным лидам (AI провал до рестарта)
            asyncio.create_task(service.retry_unanswered())

            # Если кампания была в процессе рассылки — продолжить
            if campaign.status == "sending":
                asyncio.create_task(service.start_campaign(campaign, resume=True))

            logger.info(f"Restored campaign for user {campaign.user_id} (status={campaign.status}, recipients={len(campaign.recipients)})")

        # Одно уведомление на пользователя вместо спама по каждой кампании
        if campaigns:
            notified_users = set()
            for campaign in campaigns:
                if campaign.user_id not in notified_users:
                    notified_users.add(campaign.user_id)
                    user_camps = [c for c in campaigns if c.user_id == campaign.user_id]
                    try:
                        await bot.send_message(
                            campaign.user_id,
                            f"🔄 Бот перезапущен. Восстановлено кампаний: {len(user_camps)}\n"
                            f"📱 Аккаунтов: {connected} | Ёмкость: {pool.total_daily_capacity(settings.outreach_daily_limit)}/день",
                        )
                    except Exception as e:
                        logger.warning(f"Failed to notify user {campaign.user_id}: {e}")
            logger.info(f"Restored {len(campaigns)} active campaign(s)")

    dp.startup.register(on_startup)

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
