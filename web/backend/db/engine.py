"""Создание sync/async SQLite engine и инициализация таблиц."""

import logging
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from db.models import Base

logger = logging.getLogger(__name__)


def _enable_wal(dbapi_conn, connection_record):
    """Включает WAL mode для concurrent reads."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_sync_engine(db_path: Path):
    """Sync engine для DbOutreachStorage (используется ботом)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, echo=False)
    event.listen(engine, "connect", _enable_wal)
    return engine


def get_async_engine(db_path: Path) -> AsyncEngine:
    """Async engine для DbDataReader (используется веб-API)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url, echo=False)
    return engine


def create_tables(db_path: Path) -> None:
    """Создаёт все таблицы если не существуют."""
    engine = get_sync_engine(db_path)
    Base.metadata.create_all(engine)
    engine.dispose()

    # Миграция: добавляем новые колонки в существующие таблицы
    _migrate_columns(db_path)

    logger.info(f"Database tables ensured at {db_path}")


def _migrate_columns(db_path: Path) -> None:
    """Добавляет новые колонки если их ещё нет (ALTER TABLE)."""
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    try:
        existing = {
            row[1] for row in conn.execute("PRAGMA table_info(campaigns)").fetchall()
        }
        migrations = [
            ("work_hour_start", "INTEGER"),
            ("work_hour_end", "INTEGER"),
        ]
        for col_name, col_type in migrations:
            if col_name not in existing:
                conn.execute(f"ALTER TABLE campaigns ADD COLUMN {col_name} {col_type}")
                logger.info(f"Added column campaigns.{col_name}")
        conn.commit()
    finally:
        conn.close()
