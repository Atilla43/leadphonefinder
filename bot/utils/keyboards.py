"""Inline-клавиатуры для бота."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class Keyboards:
    """Фабрика inline-клавиатур."""

    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Главное меню."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Поиск компаний", callback_data="start_scrape")],
                [InlineKeyboardButton(text="📨 AI-Продажник", callback_data="outreach_menu")],
                [InlineKeyboardButton(text="📥 Скачать шаблон", callback_data="template")],
                [InlineKeyboardButton(text="📤 Загрузить файл", callback_data="upload_hint")],
                [InlineKeyboardButton(text="📋 История", callback_data="history")],
                [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
            ]
        )

    @staticmethod
    def template_format() -> InlineKeyboardMarkup:
        """Выбор формата шаблона."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📊 Excel (.xlsx)", callback_data="template_xlsx"),
                    InlineKeyboardButton(text="📄 CSV", callback_data="template_csv"),
                ],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
            ]
        )

    @staticmethod
    def confirm_processing(file_info: str = "") -> InlineKeyboardMarkup:
        """Подтверждение обработки файла."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Начать обработку", callback_data="start_process")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_upload")],
            ]
        )

    @staticmethod
    def processing() -> InlineKeyboardMarkup:
        """Кнопки во время обработки."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏹ Отменить", callback_data="cancel_process")],
            ]
        )

    @staticmethod
    def result() -> InlineKeyboardMarkup:
        """Кнопки после завершения обработки."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📥 Excel", callback_data="download_xlsx"),
                    InlineKeyboardButton(text="📥 CSV", callback_data="download_csv"),
                ],
                [InlineKeyboardButton(text="📨 AI-Продажник", callback_data="start_outreach")],
                [InlineKeyboardButton(text="🔄 Загрузить ещё", callback_data="upload_hint")],
                [InlineKeyboardButton(text="📋 История", callback_data="history")],
            ]
        )

    @staticmethod
    def history_entry(task_id: str) -> InlineKeyboardMarkup:
        """Кнопки для записи истории."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📥 Скачать",
                        callback_data=f"history_download:{task_id}",
                    )
                ],
            ]
        )

    @staticmethod
    def back_to_menu() -> InlineKeyboardMarkup:
        """Кнопка возврата в меню."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_menu")],
            ]
        )

    @staticmethod
    def outreach_confirm(count: int) -> InlineKeyboardMarkup:
        """Подтверждение запуска AI-продажника."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"🚀 Запустить ({count} контактов)", callback_data="outreach_confirm")],
                [InlineKeyboardButton(text="✏️ Изменить оффер", callback_data="outreach_edit")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="outreach_cancel")],
            ]
        )

    @staticmethod
    def outreach_sending() -> InlineKeyboardMarkup:
        """Кнопки во время рассылки."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⏸ Пауза", callback_data="outreach_pause"),
                    InlineKeyboardButton(text="⏹ Стоп", callback_data="outreach_stop"),
                ],
            ]
        )

    @staticmethod
    def outreach_paused() -> InlineKeyboardMarkup:
        """Кнопки на паузе."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="▶️ Продолжить", callback_data="outreach_resume"),
                    InlineKeyboardButton(text="⏹ Стоп", callback_data="outreach_stop"),
                ],
            ]
        )

    @staticmethod
    def outreach_listening() -> InlineKeyboardMarkup:
        """Кнопки когда AI слушает ответы."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📊 Статус", callback_data="outreach_status")],
                [InlineKeyboardButton(text="📋 Диалоги", callback_data="outreach_dialogs")],
                [InlineKeyboardButton(text="⏹ Остановить кампанию", callback_data="outreach_stop")],
            ]
        )

    @staticmethod
    def outreach_skip_managers() -> InlineKeyboardMarkup:
        """Кнопка пропуска добавления менеджеров."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏩ Пропустить — только мне", callback_data="outreach_skip_managers")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="outreach_cancel")],
            ]
        )

    @staticmethod
    def outreach_dialogs_back() -> InlineKeyboardMarkup:
        """Кнопки на экране диалогов."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔥 Тёплые", callback_data="dial_filter:warm"),
                    InlineKeyboardButton(text="💬 Активные", callback_data="dial_filter:talking"),
                    InlineKeyboardButton(text="Все", callback_data="dial_filter:all"),
                ],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="outreach_status")],
            ]
        )

    @staticmethod
    def outreach_file_result() -> InlineKeyboardMarkup:
        """Кнопки после загрузки файла с телефонами."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📨 AI-Продажник", callback_data="start_outreach")],
                [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_menu")],
            ]
        )

    @staticmethod
    def outreach_source(has_campaign: bool = False) -> InlineKeyboardMarkup:
        """Выбор источника контактов для AI-продажника."""
        buttons = [
            [InlineKeyboardButton(text="📄 Загрузить файл с контактами", callback_data="outreach_upload")],
            [InlineKeyboardButton(text="🔍 Из результатов поиска", callback_data="start_outreach")],
        ]
        if has_campaign:
            buttons.append([
                InlineKeyboardButton(text="📋 Диалоги", callback_data="outreach_dialogs"),
                InlineKeyboardButton(text="📊 Статус", callback_data="outreach_status"),
            ])
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def outreach_dialog_limit() -> InlineKeyboardMarkup:
        """Выбор количества AI-диалогов."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="5 диалогов", callback_data="outreach_limit:5"),
                    InlineKeyboardButton(text="10 диалогов", callback_data="outreach_limit:10"),
                ],
                [
                    InlineKeyboardButton(text="20 диалогов", callback_data="outreach_limit:20"),
                    InlineKeyboardButton(text="Все", callback_data="outreach_limit:0"),
                ],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="outreach_cancel")],
            ]
        )

    @staticmethod
    def enrichment_limit() -> InlineKeyboardMarkup:
        """Выбор лимита обогащения."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="50 пробивов", callback_data="enrich_limit:50"),
                    InlineKeyboardButton(text="100 пробивов", callback_data="enrich_limit:100"),
                ],
                [
                    InlineKeyboardButton(text="200 пробивов", callback_data="enrich_limit:200"),
                    InlineKeyboardButton(text="Все", callback_data="enrich_limit:0"),
                ],
                [InlineKeyboardButton(text="❌ Пропустить обогащение", callback_data="enrich_limit:skip")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
            ]
        )
