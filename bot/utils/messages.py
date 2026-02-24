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
    def access_denied() -> str:
        """Доступ запрещён."""
        return (
            "🚫 <b>Доступ запрещён</b>\n\n"
            "У вас нет доступа к этому боту.\n"
            "Обратитесь к администратору."
        )
