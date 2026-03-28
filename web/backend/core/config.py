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


settings = Settings()
