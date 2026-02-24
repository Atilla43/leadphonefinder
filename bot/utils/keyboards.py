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
