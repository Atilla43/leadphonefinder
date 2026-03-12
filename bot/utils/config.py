from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Конфигурация приложения."""

    # Telegram Bot
    bot_token: str

    # Telethon (userbot для Шерлока) — опционально если используется API
    telethon_api_id: Optional[int] = None
    telethon_api_hash: Optional[str] = None
    telethon_phone: Optional[str] = None
    telethon_session_name: str = "userbot_session"

    # Шерлок бот (Telegram)
    sherlock_bot_username: str = "sherlock_osint_bot"

    # Sherlock API (если доступен — используется вместо Telegram)
    sherlock_api_url: Optional[str] = None  # https://api.sherlockbot.org/v1
    sherlock_api_key: Optional[str] = None

    # Лимиты
    request_delay_seconds: float = 3.0
    max_file_size_mb: int = 10
    max_rows: int = 100
    progress_update_interval: int = 5

    # Scrapper v2
    scrapper_max_results: int = 100
    scrapper_use_twogis: bool = True
    scrapper_use_yandex: bool = True
    scrapper_headless: bool = True
    scrapper_delay_min: float = 1.0
    scrapper_delay_max: float = 3.0

    # Кеширование результатов скраппинга
    scrapper_cache_ttl_hours: int = 24
    scrapper_cache_dir: str = "data/cache"

    # DaData (для поиска ИНН по названию)
    dadata_token: Optional[str] = None

    # LLM для парсинга сложных запросов (опционально)
    # Поддерживаются: openai, gigachat, yandexgpt
    llm_provider: Optional[str] = None  # "openai", "gigachat", "yandexgpt"
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None  # "gpt-4o-mini", "GigaChat", "yandexgpt-lite"
    llm_folder_id: Optional[str] = None  # Только для YandexGPT

    # Доступ (whitelist user IDs, разделённые запятой)
    allowed_user_ids: Optional[str] = None

    # AI Outreach
    outreach_delay_min: float = 5.0
    outreach_delay_max: float = 15.0
    outreach_reply_delay_min: float = 3.0
    outreach_reply_delay_max: float = 8.0
    outreach_daily_limit: int = 30
    outreach_ping_interval_hours: int = 4
    outreach_max_pings: int = 3
    outreach_sticker_pack: str = "real_cats"
    outreach_work_hour_start: int = 10
    outreach_work_hour_end: int = 17

    # OpenRouter (для AI-диалогов)
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "openai/gpt-4o-mini"

    # История
    history_retention_days: int = 7

    # Redis (для персистентности задач)
    redis_url: Optional[str] = None  # redis://localhost:6379
    task_ttl_seconds: int = 3600  # 1 час

    @property
    def allowed_users(self) -> list[int]:
        """Список разрешённых user_id."""
        if not self.allowed_user_ids:
            return []
        return [int(uid.strip()) for uid in self.allowed_user_ids.split(",") if uid.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        """Максимальный размер файла в байтах."""
        return self.max_file_size_mb * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
