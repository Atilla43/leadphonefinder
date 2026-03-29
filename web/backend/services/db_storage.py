"""DB-backed OutreachStorage — drop-in замена для JSON-хра��илища.

Использует sync sqlite3 напрямую, т.к. OutreachService._save()
вызывается из sync контекст��.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Глобальный путь к БД — устанавливается при старте
_DB_PATH: Optional[Path] = None

# Callback для WebSocket уведомлений при save()
_on_save_callback = None


def set_db_path(path: Path) -> None:
    global _DB_PATH
    _DB_PATH = path


def set_on_save_callback(callback) -> None:
    global _on_save_callback
    _on_save_callback = callback


class DbOutreachStorage:
    """Персистентное хранилище кампаний в SQLite.

    Интерфейс идентичен OutreachStorage из bot/services/outreach_storage.py.
    """

    def __init__(self) -> None:
        db = _DB_PATH or Path("data/signal_grid.db")
        self._db_path = str(db)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, campaign) -> None:
        """Сохраняет кампанию (upsert campaign + recipients + messages)."""
        conn = self._conn()
        try:
            now = datetime.now(timezone.utc).isoformat()

            # Upsert campaign
            conn.execute(
                """INSERT INTO campaigns
                   (campaign_id, user_id, name, offer, status,
                    sent_count, warm_count, rejected_count, not_found_count,
                    manager_ids, system_prompt, service_info,
                    work_hour_start, work_hour_end,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(campaign_id) DO UPDATE SET
                    user_id=excluded.user_id, name=excluded.name,
                    offer=excluded.offer, status=excluded.status,
                    sent_count=excluded.sent_count, warm_count=excluded.warm_count,
                    rejected_count=excluded.rejected_count,
                    not_found_count=excluded.not_found_count,
                    manager_ids=excluded.manager_ids,
                    system_prompt=excluded.system_prompt,
                    service_info=excluded.service_info,
                    work_hour_start=excluded.work_hour_start,
                    work_hour_end=excluded.work_hour_end,
                    updated_at=excluded.updated_at
                """,
                (
                    campaign.campaign_id,
                    campaign.user_id,
                    campaign.name,
                    campaign.offer,
                    campaign.status,
                    campaign.sent_count,
                    campaign.warm_count,
                    campaign.rejected_count,
                    campaign.not_found_count,
                    json.dumps(campaign.manager_ids),
                    campaign.system_prompt,
                    campaign.service_info,
                    getattr(campaign, "work_hour_start", None),
                    getattr(campaign, "work_hour_end", None),
                    now,
                    now,
                ),
            )

            for r in campaign.recipients:
                last_msg = r.last_message_at.isoformat() if r.last_message_at else None

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
                        campaign.campaign_id,
                        r.phone,
                        r.company_name,
                        r.contact_name,
                        r.category,
                        r.rating,
                        r.reviews_count,
                        r.website,
                        r.working_hours,
                        r.address,
                        r.director_name,
                        r.telegram_user_id,
                        r.account_phone,
                        r.referral_context,
                        r.status,
                        last_msg,
                        r.ping_count,
                        r.error_message,
                    ),
                )

                # Получаем recipient_id
                row = conn.execute(
                    "SELECT id FROM recipients WHERE campaign_id=? AND phone=?",
                    (campaign.campaign_id, r.phone),
                ).fetchone()
                if not row:
                    continue
                recipient_id = row["id"]

                # Append only new messages
                existing_count = conn.execute(
                    "SELECT COUNT(*) as cnt FROM messages WHERE recipient_id=?",
                    (recipient_id,),
                ).fetchone()["cnt"]

                new_messages = r.conversation_history[existing_count:]
                for msg in new_messages:
                    conn.execute(
                        """INSERT INTO messages (recipient_id, role, content, created_at)
                           VALUES (?, ?, ?, ?)""",
                        (
                            recipient_id,
                            msg.get("role", "user"),
                            msg.get("content", ""),
                            now,
                        ),
                    )

            conn.commit()
            logger.debug(f"Campaign {campaign.campaign_id} saved to DB")

            # Уведомляем WebSocket
            if _on_save_callback:
                try:
                    _on_save_callback(campaign)
                except Exception:
                    pass

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save campaign {campaign.campaign_id}: {e}")
            raise
        finally:
            conn.close()

    def load(self, user_id: int, campaign_id: str = ""):
        """Загружает кампанию из DB."""
        # Импортируем тут чтобы не создавать циклических зависимостей
        from bot.models.outreach import OutreachCampaign, OutreachRecipient

        conn = self._conn()
        try:
            # Определяем campaign_id для поиска
            if campaign_id and campaign_id != str(user_id):
                row = conn.execute(
                    "SELECT * FROM campaigns WHERE campaign_id=?",
                    (campaign_id,),
                ).fetchone()
            else:
                # Старый формат — ищем по user_id
                row = conn.execute(
                    "SELECT * FROM campaigns WHERE campaign_id=? OR user_id=? ORDER BY created_at DESC LIMIT 1",
                    (str(user_id), user_id),
                ).fetchone()

            if not row:
                return None

            cid = row["campaign_id"]
            recipients = self._load_recipients(conn, cid)

            campaign = OutreachCampaign(
                user_id=row["user_id"],
                offer=row["offer"],
                recipients=recipients,
                campaign_id=cid,
                name=row["name"] or "",
                status=row["status"],
                sent_count=row["sent_count"],
                warm_count=row["warm_count"],
                rejected_count=row["rejected_count"],
                not_found_count=row["not_found_count"],
                manager_ids=json.loads(row["manager_ids"] or "[]"),
                system_prompt=row["system_prompt"] or "",
                service_info=row["service_info"] or "",
            )
            campaign.work_hour_start = row["work_hour_start"]
            campaign.work_hour_end = row["work_hour_end"]
            return campaign
        except Exception as e:
            logger.error(f"Failed to load campaign for user {user_id}: {e}")
            return None
        finally:
            conn.close()

    def delete(self, user_id: int, campaign_id: str = "") -> None:
        """Удаляет кампанию (CASCADE удалит recipients и messages)."""
        conn = self._conn()
        try:
            if campaign_id and campaign_id != str(user_id):
                conn.execute(
                    "DELETE FROM campaigns WHERE campaign_id=?", (campaign_id,)
                )
            else:
                conn.execute(
                    "DELETE FROM campaigns WHERE campaign_id=? OR (user_id=? AND campaign_id=?)",
                    (str(user_id), user_id, str(user_id)),
                )
            conn.commit()
            logger.debug(f"Campaign {campaign_id or user_id} deleted from DB")
        finally:
            conn.close()

    def load_all_active(self):
        """Загружает все активные кампании."""
        from bot.models.outreach import OutreachCampaign

        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM campaigns WHERE status IN ('sending', 'listening', 'paused')"
            ).fetchall()

            campaigns = []
            for row in rows:
                recipients = self._load_recipients(conn, row["campaign_id"])
                campaign = OutreachCampaign(
                    user_id=row["user_id"],
                    offer=row["offer"],
                    recipients=recipients,
                    campaign_id=row["campaign_id"],
                    name=row["name"] or "",
                    status=row["status"],
                    sent_count=row["sent_count"],
                    warm_count=row["warm_count"],
                    rejected_count=row["rejected_count"],
                    not_found_count=row["not_found_count"],
                    manager_ids=json.loads(row["manager_ids"] or "[]"),
                    system_prompt=row["system_prompt"] or "",
                    service_info=row["service_info"] or "",
                )
                campaign.work_hour_start = row["work_hour_start"]
                campaign.work_hour_end = row["work_hour_end"]
                campaigns.append(campaign)
            return campaigns
        except Exception as e:
            logger.error(f"Failed to load active campaigns: {e}")
            return []
        finally:
            conn.close()

    def load_user_campaigns(self, user_id: int):
        """Загружает все кампании пользователя."""
        from bot.models.outreach import OutreachCampaign

        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM campaigns WHERE user_id=? AND status IN ('sending', 'listening', 'paused')",
                (user_id,),
            ).fetchall()

            campaigns = []
            for row in rows:
                recipients = self._load_recipients(conn, row["campaign_id"])
                campaign = OutreachCampaign(
                    user_id=row["user_id"],
                    offer=row["offer"],
                    recipients=recipients,
                    campaign_id=row["campaign_id"],
                    name=row["name"] or "",
                    status=row["status"],
                    sent_count=row["sent_count"],
                    warm_count=row["warm_count"],
                    rejected_count=row["rejected_count"],
                    not_found_count=row["not_found_count"],
                    manager_ids=json.loads(row["manager_ids"] or "[]"),
                    system_prompt=row["system_prompt"] or "",
                    service_info=row["service_info"] or "",
                )
                campaign.work_hour_start = row["work_hour_start"]
                campaign.work_hour_end = row["work_hour_end"]
                campaigns.append(campaign)
            return campaigns
        except Exception as e:
            logger.error(f"Failed to load campaigns for user {user_id}: {e}")
            return []
        finally:
            conn.close()

    def _load_recipients(self, conn, campaign_id: str):
        """Загружает recipients с conversation_history д��я кампании."""
        from bot.models.outreach import OutreachRecipient

        rows = conn.execute(
            "SELECT * FROM recipients WHERE campaign_id=?", (campaign_id,)
        ).fetchall()

        recipients = []
        for row in rows:
            # Загружаем messages
            messages = conn.execute(
                "SELECT role, content FROM messages WHERE recipient_id=? ORDER BY id",
                (row["id"],),
            ).fetchall()
            conversation_history = [
                {"role": m["role"], "content": m["content"]} for m in messages
            ]

            last_msg = None
            if row["last_message_at"]:
                try:
                    last_msg = datetime.fromisoformat(row["last_message_at"])
                except (ValueError, TypeError):
                    pass

            recipients.append(
                OutreachRecipient(
                    phone=row["phone"],
                    company_name=row["company_name"] or "",
                    contact_name=row["contact_name"],
                    category=row["category"],
                    rating=row["rating"],
                    reviews_count=row["reviews_count"],
                    website=row["website"],
                    working_hours=row["working_hours"],
                    address=row["address"],
                    director_name=row["director_name"],
                    telegram_user_id=row["telegram_user_id"],
                    account_phone=row["account_phone"],
                    referral_context=row["referral_context"],
                    status=row["status"] or "pending",
                    conversation_history=conversation_history,
                    last_message_at=last_msg,
                    ping_count=row["ping_count"] or 0,
                    error_message=row["error_message"],
                )
            )
        return recipients
