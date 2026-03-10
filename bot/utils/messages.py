"""Текстовые сообщения для бота."""

from bot.models.company import EnrichmentResult, EnrichmentStatus
from bot.services.phone_extractor import mask_phone
from bot.utils.config import settings


class Messages:
    """Шаблоны сообщений."""

    @staticmethod
    def welcome() -> str:
        """Приветственное сообщение."""
        return (
            "👋 <b>Привет!</b> Я помогу найти телефоны собственников компаний по ИНН.\n\n"
            "📋 <b>Как это работает:</b>\n"
            "1. Загрузи файл Excel или CSV с колонками «ИНН» и «Название»\n"
            "2. Я найду телефоны по каждому ИНН\n"
            "3. Получи готовый файл с результатами\n\n"
            "⬇️ <b>Скачай шаблон файла или загрузи свой:</b>\n\n"
            f"💡 <i>Поддерживаю до {settings.max_rows} компаний за раз</i>"
        )

    @staticmethod
    def help_text() -> str:
        """Текст помощи."""
        return (
            "❓ <b>Помощь</b>\n\n"
            "<b>Как пользоваться:</b>\n"
            "1. Скачай шаблон файла (Excel или CSV)\n"
            "2. Заполни его данными компаний (ИНН и Название)\n"
            "3. Загрузи файл в бота\n"
            "4. Дождись обработки и скачай результат\n\n"
            "<b>Форматы файлов:</b>\n"
            "• Excel (.xlsx) — рекомендуется\n"
            "• CSV — с кодировкой UTF-8\n\n"
            "<b>Ограничения:</b>\n"
            f"• Максимум {settings.max_rows} записей в файле\n"
            "• Максимальный размер файла: 10 МБ\n\n"
            "<b>Статусы результата:</b>\n"
            "• success — телефон найден\n"
            "• not_found — телефон не найден\n"
            "• invalid_inn — некорректный ИНН\n"
            "• error — ошибка при поиске"
        )

    @staticmethod
    def upload_hint() -> str:
        """Подсказка для загрузки файла."""
        return (
            "📤 <b>Загрузка файла</b>\n\n"
            "Отправь мне файл Excel (.xlsx) или CSV с колонками:\n"
            "• <b>ИНН</b> — ИНН компании\n"
            "• <b>Название</b> — название компании\n\n"
            "💡 <i>Можешь скачать шаблон, если нужен пример</i>"
        )

    @staticmethod
    def file_received(filename: str, stats: dict) -> str:
        """Сообщение после получения файла."""
        return (
            f"📂 <b>Файл получен:</b> {filename}\n\n"
            f"📊 <b>Найдено записей:</b> {stats['total']}\n"
            f"├ Корректных ИНН: {stats['valid']}\n"
            f"├ Некорректных ИНН: {stats['invalid']} <i>(будут пропущены)</i>\n"
            f"└ Дубликатов: {stats['duplicates']}\n\n"
            "Нажми <b>«Начать обработку»</b> для поиска телефонов."
        )

    @staticmethod
    def file_error(error: str) -> str:
        """Сообщение об ошибке файла."""
        return (
            "❌ <b>Не удалось прочитать файл</b>\n\n"
            f"Причина: {error}\n\n"
            "💡 <i>Убедись, что файл в формате .xlsx или .csv "
            "и содержит колонки «ИНН» и «Название»</i>"
        )

    @staticmethod
    def file_too_large(max_size_mb: int) -> str:
        """Файл слишком большой."""
        return (
            f"📁 <b>Файл слишком большой</b>\n\n"
            f"Максимальный размер: {max_size_mb} МБ\n\n"
            "💡 <i>Попробуй разбить файл на части</i>"
        )

    @staticmethod
    def too_many_rows(max_rows: int, actual_rows: int) -> str:
        """Слишком много строк."""
        return (
            f"📊 <b>Слишком много записей</b>\n\n"
            f"В файле: {actual_rows} записей\n"
            f"Максимум: {max_rows} записей\n\n"
            "💡 <i>Разбей файл на несколько частей</i>"
        )

    @staticmethod
    def processing_started(total: int) -> str:
        """Начало обработки."""
        return (
            f"⏳ <b>Обработка начата...</b>\n\n"
            f"Всего записей: {total}\n\n"
            "💡 <i>Это может занять несколько минут</i>"
        )

    @staticmethod
    def processing_progress(
        current: int, total: int, last_results: list = None
    ) -> str:
        """Прогресс обработки."""
        progress = int((current / total) * 20)
        bar = "█" * progress + "░" * (20 - progress)
        percent = int((current / total) * 100)

        text = (
            f"⏳ <b>Обработка...</b>\n\n"
            f"{bar} {current}/{total} ({percent}%)\n"
        )

        if last_results:
            text += "\n<b>Последние результаты:</b>\n"
            for company in last_results[-3:]:
                if company.status == EnrichmentStatus.SUCCESS:
                    phone = mask_phone(company.phone.split(",")[0]) if company.phone else ""
                    text += f"✅ {company.name[:20]}... — {phone}\n"
                elif company.status == EnrichmentStatus.NOT_FOUND:
                    text += f"⚠️ {company.name[:20]}... — не найдено\n"
                elif company.status == EnrichmentStatus.INVALID_INN:
                    text += f"❌ {company.name[:20]}... — невалидный ИНН\n"
                else:
                    text += f"🔴 {company.name[:20]}... — ошибка\n"

        return text

    @staticmethod
    def processing_complete(result: EnrichmentResult) -> str:
        """Обработка завершена."""
        success_rate = result.success_rate

        # Форматируем время
        minutes = int(result.processing_time_seconds // 60)
        seconds = int(result.processing_time_seconds % 60)
        time_str = f"{minutes} мин {seconds} сек" if minutes else f"{seconds} сек"

        return (
            "✅ <b>Обработка завершена!</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"├ Всего: {result.total}\n"
            f"├ ✅ Найдено телефонов: {result.success_count} ({success_rate:.0f}%)\n"
            f"├ ⚠️ Не найдено: {result.not_found_count}\n"
            f"├ ❌ Некорректных ИНН: {result.invalid_count}\n"
            f"├ 🔴 Ошибок: {result.error_count}\n"
            f"└ ⏱ Время: {time_str}\n\n"
            "Выбери формат для скачивания:"
        )

    @staticmethod
    def processing_cancelled() -> str:
        """Обработка отменена."""
        return (
            "⏹ <b>Обработка отменена</b>\n\n"
            "Результаты частичной обработки не сохранены."
        )

    @staticmethod
    def no_history() -> str:
        """История пуста."""
        return (
            "📋 <b>История загрузок</b>\n\n"
            "<i>Пока нет обработанных файлов</i>\n\n"
            "💡 Загрузи файл, чтобы история появилась"
        )

    @staticmethod
    def outreach_file_received(filename: str, count: int) -> str:
        """Файл с телефонами для outreach получен."""
        return (
            f"📂 <b>Файл получен:</b> {filename}\n\n"
            f"📱 <b>Найдено контактов:</b> {count}\n\n"
            "Нажмите <b>«📨 AI-Продажник»</b> чтобы запустить рассылку."
        )

    # ─── AI-Продажник ───

    @staticmethod
    def outreach_menu() -> str:
        """Меню AI-Продажника."""
        return (
            "📨 <b>AI-Продажник</b>\n\n"
            "Выберите источник контактов:\n\n"
            "📄 <b>Загрузить файл</b> — загрузите Excel с телефонами, именами, компаниями\n"
            "🔍 <b>Из результатов поиска</b> — используйте контакты из последнего поиска"
        )

    @staticmethod
    def outreach_upload_hint() -> str:
        """Подсказка для загрузки файла outreach."""
        return (
            "📄 <b>Загрузка контактов для AI-Продажника</b>\n\n"
            "Отправьте Excel файл (.xlsx) с контактами.\n\n"
            "📋 <b>Обязательные колонки:</b>\n"
            "• <b>Телефон</b> — номер телефона контакта\n"
            "• <b>Компания</b> — название компании\n\n"
            "📋 <b>Опциональные колонки:</b>\n"
            "• <b>Контакт</b> — имя контактного лица\n\n"
            "💡 <i>Нажмите кнопку ниже, чтобы скачать шаблон</i>"
        )

    @staticmethod
    def outreach_dialog_limit(count: int) -> str:
        """Выбор количества диалогов."""
        return (
            f"📱 <b>Загружено контактов:</b> {count}\n\n"
            "Сколько AI-диалогов вести?\n\n"
            "💡 <i>AI напишет первое сообщение каждому контакту и будет "
            "автоматически отвечать на входящие</i>"
        )

    @staticmethod
    def outreach_prompt(count: int) -> str:
        """Промпт для ввода оффера."""
        return (
            f"📨 <b>AI-Продажник</b>\n\n"
            f"Найдено <b>{count}</b> контактов с телефонами.\n\n"
            "Введите текст <b>оффера</b> — он будет отправлен после приветствия:\n\n"
            "<i>Пример:</i>\n"
            "<code>Мы помогаем таким бизнесам увеличить выручку на 20-30% "
            "за счёт digital-маркетинга. Можем провести бесплатный аудит "
            "за 15 минут — покажу 3 точки роста. Когда удобнее?</code>"
        )

    @staticmethod
    def outreach_preview(offer: str, name: str, company: str, count: int) -> str:
        """Превью первого сообщения."""
        preview = f"Здравствуйте, {name}! Пишу вам по поводу {company}.\n\n\n{offer}"
        return (
            "📨 <b>Превью первого сообщения:</b>\n\n"
            f"<code>{preview}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Получателей: <b>{count}</b>\n"
            f"⏱ Задержка: {int(settings.outreach_delay_min)}-{int(settings.outreach_delay_max)} сек\n"
            f"📱 Лимит/день: {settings.outreach_daily_limit}\n\n"
            "⚠️ <b>Внимание:</b> Сообщения будут отправлены через Telegram "
            "от имени вашего аккаунта. AI будет автоматически отвечать на "
            "входящие сообщения и пинговать при игноре (каждые 4ч, 9:00-21:00 МСК)."
        )

    @staticmethod
    def outreach_progress(sent: int, total: int, campaign) -> str:
        """Прогресс рассылки."""
        progress = int((sent / total) * 20) if total else 0
        bar = "█" * progress + "░" * (20 - progress)
        percent = int((sent / total) * 100) if total else 0
        return (
            f"📨 <b>Рассылка...</b>\n\n"
            f"{bar} {sent}/{total} ({percent}%)\n\n"
            f"✅ Отправлено: {campaign.sent_count}\n"
            f"❌ Нет в Telegram: {campaign.not_found_count}"
        )

    @staticmethod
    def outreach_warm_lead(recipient) -> str:
        """Уведомление о тёплом лиде."""
        return (
            f"🔥 <b>ТЁПЛЫЙ ЛИД!</b>\n\n"
            f"🏢 {recipient.company_name}\n"
            f"👤 {recipient.contact_name or 'N/A'}\n"
            f"📱 {recipient.phone}\n\n"
            "Лид согласился на встречу/звонок.\n"
            "Подхватите диалог в TG Master!"
        )

    @staticmethod
    def outreach_complete(campaign) -> str:
        """Итоги кампании."""
        return (
            "📨 <b>Кампания завершена!</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"├ Отправлено: {campaign.sent_count}\n"
            f"├ 🔥 Тёплых лидов: {campaign.warm_count}\n"
            f"├ ❌ Отказов: {campaign.rejected_count}\n"
            f"├ 📵 Нет в Telegram: {campaign.not_found_count}\n"
            f"└ 😶 Без ответа: {sum(1 for r in campaign.recipients if r.status == 'no_response')}"
        )

    @staticmethod
    def outreach_status(campaign) -> str:
        """Текущий статус кампании."""
        active = sum(1 for r in campaign.recipients if r.status in ("sent", "talking"))
        return (
            "📨 <b>Статус AI-Продажника</b>\n\n"
            f"📊 Активных диалогов: {active}\n"
            f"🔥 Тёплых лидов: {campaign.warm_count}\n"
            f"❌ Отказов: {campaign.rejected_count}\n"
            f"😶 Без ответа: {sum(1 for r in campaign.recipients if r.status == 'no_response')}\n"
            f"📵 Нет в Telegram: {campaign.not_found_count}"
        )

    @staticmethod
    def access_denied() -> str:
        """Доступ запрещён."""
        return (
            "🚫 <b>Доступ запрещён</b>\n\n"
            "У вас нет доступа к этому боту.\n"
            "Обратитесь к администратору."
        )
