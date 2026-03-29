"""Миграция данных из JSON-файлов в SQLite.

Запуск:
    cd web/backend
    python -m db.migration
"""

import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Добавляем backend и project root в path
backend_dir = str(Path(__file__).resolve().parent.parent)
project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
for p in (backend_dir, project_root):
    if p not in sys.path:
        sys.path.insert(0, p)

from core.config import settings
from db.engine import create_tables

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _get_json_files() -> list[Path]:
    """Находит все JSON-файлы кампаний."""
    outreach_dir = settings.outreach_dir
    if not outreach_dir.exists():
        logger.warning(f"Outreach dir not found: {outreach_dir}")
        return []
    return sorted(outreach_dir.glob("campaign_*.json"))


def _migrate_campaign(conn: sqlite3.Connection, data: dict, source: str) -> None:
    """Мигрирует одну кампанию из JSON dict в DB."""
    campaign_id = data.get("campaign_id") or str(data.get("user_id", ""))
    user_id = data.get("user_id", 0)
    now = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"  Migrating campaign {campaign_id} "
        f"({len(data.get('recipients', []))} recipients) from {source}"
    )

    # Upsert campaign
    conn.execute(
        """INSERT INTO campaigns
           (campaign_id, user_id, name, offer, status,
            sent_count, warm_count, rejected_count, not_found_count,
            manager_ids, system_prompt, service_info, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(campaign_id) DO UPDATE SET
            user_id=excluded.user_id, name=excluded.name,
            offer=excluded.offer, status=excluded.status,
            sent_count=excluded.sent_count, warm_count=excluded.warm_count,
            rejected_count=excluded.rejected_count,
            not_found_count=excluded.not_found_count,
            manager_ids=excluded.manager_ids,
            system_prompt=excluded.system_prompt,
            service_info=excluded.service_info,
            updated_at=excluded.updated_at
        """,
        (
            campaign_id,
            user_id,
            data.get("name", ""),
            data.get("offer", ""),
            data.get("status", "pending"),
            data.get("sent_count", 0),
            data.get("warm_count", 0),
            data.get("rejected_count", 0),
            data.get("not_found_count", 0),
            json.dumps(data.get("manager_ids", [])),
            data.get("system_prompt", ""),
            data.get("service_info", ""),
            now,
            now,
        ),
    )

    msg_count = 0
    for r in data.get("recipients", []):
        phone = r.get("phone", "")
        if not phone:
            continue

        last_msg_at = r.get("last_message_at")

        # Upsert recipient
        conn.execute(
            """INSERT INTO recipients
               (campaign_id, phone, company_name, contact_name, category,
                rating, reviews_count, website, working_hours, address,
                director_name, telegram_user_id, account_phone,
                referral_context, status, last_message_at, ping_count,
                error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(campaign_id, phone) DO UPDATE SET
                company_name=excluded.company_name,
                contact_name=excluded.contact_name,
                category=excluded.category,
                rating=excluded.rating,
                reviews_count=excluded.reviews_count,
                website=excluded.website,
                working_hours=excluded.working_hours,
                address=excluded.address,
                director_name=excluded.director_name,
                telegram_user_id=excluded.telegram_user_id,
                account_phone=excluded.account_phone,
                referral_context=excluded.referral_context,
                status=excluded.status,
                last_message_at=excluded.last_message_at,
                ping_count=excluded.ping_count,
                error_message=excluded.error_message
            """,
            (
                campaign_id,
                phone,
                r.get("company_name", ""),
                r.get("contact_name"),
                r.get("category"),
                r.get("rating"),
                r.get("reviews_count"),
                r.get("website"),
                r.get("working_hours"),
                r.get("address"),
                r.get("director_name"),
                r.get("telegram_user_id"),
                r.get("account_phone"),
                r.get("referral_context"),
                r.get("status", "pending"),
                last_msg_at,
                r.get("ping_count", 0),
                r.get("error_message"),
            ),
        )

        # Получаем recipient_id
        row = conn.execute(
            "SELECT id FROM recipients WHERE campaign_id=? AND phone=?",
            (campaign_id, phone),
        ).fetchone()
        if not row:
            continue
        recipient_id = row[0]

        # Удаляем старые messages для этого recipient (re-import)
        conn.execute(
            "DELETE FROM messages WHERE recipient_id=?", (recipient_id,)
        )

        # Вставляем все messages
        history = r.get("conversation_history", [])
        for msg in history:
            conn.execute(
                """INSERT INTO messages (recipient_id, role, content, created_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    recipient_id,
                    msg.get("role", "user"),
                    msg.get("content", ""),
                    last_msg_at or now,
                ),
            )
            msg_count += 1

    logger.info(f"    → {len(data.get('recipients', []))} recipients, {msg_count} messages")


def migrate() -> None:
    """Запускает миграцию JSON → SQLite."""
    db_path = settings.db_path
    logger.info(f"DB path: {db_path}")

    # Создаём таблицы
    create_tables(db_path)

    json_files = _get_json_files()
    if not json_files:
        logger.info("No JSON campaign files found — nothing to migrate.")
        return

    logger.info(f"Found {len(json_files)} campaign file(s) to migrate")

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        for json_file in json_files:
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                _migrate_campaign(conn, data, json_file.name)
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to read {json_file.name}: {e}")
                continue

        conn.commit()
        logger.info("Migration completed successfully!")

        # Проверяем результаты
        campaigns = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
        recipients = conn.execute("SELECT COUNT(*) FROM recipients").fetchone()[0]
        messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        logger.info(f"DB stats: {campaigns} campaigns, {recipients} recipients, {messages} messages")

    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

    # Мигрируем аккаунты
    accounts_json = settings.project_root / "data" / "telethon_accounts.json"
    if accounts_json.exists():
        from services.db_account_storage import migrate_accounts_json_to_db
        count = migrate_accounts_json_to_db(accounts_json, db_path)
        if count:
            logger.info(f"Accounts: {count} migrated from JSON to DB")
    else:
        logger.info("No telethon_accounts.json found — skipping accounts migration")


if __name__ == "__main__":
    migrate()
