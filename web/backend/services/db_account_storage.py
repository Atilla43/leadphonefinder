"""DB-backed хранение Telethon-аккаунтов.

Заменяет JSON-файл telethon_accounts.json на таблицу accounts в SQLite.
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def db_save_accounts(accounts: list, db_path: Path) -> None:
    """Сохраняет список аккаунтов в DB (полная перезапись)."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        # Удаляем все и вставляем заново (аккаунтов мало, проще чем upsert)
        conn.execute("DELETE FROM accounts")
        for a in accounts:
            conn.execute(
                """INSERT INTO accounts (phone, api_id, api_hash, session_name, active)
                   VALUES (?, ?, ?, ?, ?)""",
                (a.phone, a.api_id, a.api_hash, a.session_name, a.active),
            )
        conn.commit()
        logger.debug(f"Saved {len(accounts)} account(s) to DB")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save accounts to DB: {e}")
    finally:
        conn.close()


def db_load_accounts(pool, db_path: Path) -> None:
    """Загружает аккаунты из DB в AccountPool."""
    from bot.services.account_pool import AccountInfo

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM accounts").fetchall()
        pool.accounts = [
            AccountInfo(
                phone=row["phone"],
                api_id=row["api_id"],
                api_hash=row["api_hash"],
                session_name=row["session_name"],
                active=bool(row["active"]),
            )
            for row in rows
        ]
        logger.debug(f"Loaded {len(pool.accounts)} account(s) from DB")
    except Exception as e:
        logger.error(f"Failed to load accounts from DB: {e}")
        pool.accounts = []
    finally:
        conn.close()


def migrate_accounts_json_to_db(json_path: Path, db_path: Path) -> int:
    """Мигрирует аккаунты из JSON-файла в DB. Возвращает количество."""
    import json

    if not json_path.exists():
        return 0

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0

    if not data:
        return 0

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        for item in data:
            conn.execute(
                """INSERT OR REPLACE INTO accounts (phone, api_id, api_hash, session_name, active)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    item["phone"],
                    item["api_id"],
                    item["api_hash"],
                    item["session_name"],
                    item.get("active", True),
                ),
            )
        conn.commit()
        logger.info(f"Migrated {len(data)} account(s) from JSON to DB")
        return len(data)
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to migrate accounts: {e}")
        return 0
    finally:
        conn.close()
