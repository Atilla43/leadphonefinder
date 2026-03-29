"""Конфигурация веб-платформы."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки FastAPI backend."""

    # Пути к данным бота (относительно корня проекта)
    project_root: Path = Path(__file__).resolve().parent.parent.parent.parent
    outreach_dir: Path = Path("")
    cache_dir: Path = Path("")
    accounts_file: Path = Path("")

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]

    # DataReader
    data_cache_ttl_seconds: int = 5

    # WebSocket
    ws_check_interval_seconds: float = 3.0

    # OpenRouter (AI-диалоги)
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"

    # Groq (транскрибация голосовых)
    groq_api_key: str = ""

    # Telegram Bot (уведомления менеджерам)
    telegram_bot_token: str = ""

    # Владелец (Telegram user ID для уведомлений по умолчанию)
    owner_telegram_id: int = 0

    # Outreach settings
    outreach_daily_limit: int = 30
    outreach_work_hour_start: int = 10
    outreach_work_hour_end: int = 17
    outreach_sticker_pack: str = "catsunicmass"
    outreach_sticker_index: int = 33
    outreach_ping_interval_hours: int = 4
    outreach_max_pings: int = 3

    def model_post_init(self, __context: object) -> None:
        if not self.outreach_dir or str(self.outreach_dir) == ".":
            self.outreach_dir = self.project_root / "data" / "outreach"
        if not self.cache_dir or str(self.cache_dir) == ".":
            self.cache_dir = self.project_root / "data" / "cache"
        if not self.accounts_file or str(self.accounts_file) == ".":
            self.accounts_file = self.project_root / "data" / "telethon_accounts.json"

    class Config:
        env_prefix = "WEB_"
        env_file = ".env"
        extra = "ignore"


settings = Settings()
