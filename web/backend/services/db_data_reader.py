"""Async DB-based DataReader — замена JSON DataReader.

Возвращает те же dict-структуры, что и DataReader,
чтобы не менять API routes.
"""

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class DbDataReader:
    """Читает данные из SQLite через async SQLAlchemy."""

    def __init__(
        self,
        engine: AsyncEngine,
        cache_dir: Path,
        accounts_file: Path,
    ) -> None:
        self._engine = engine
        # Кеш скраппера остаётся в JSON
        self.cache_dir = cache_dir
        self.accounts_file = accounts_file

    # ── Кампании ──

    async def get_all_campaigns(self) -> list[dict]:
        """Все кампании с recipients (dict формат)."""
        async with self._engine.connect() as conn:
            rows = await conn.execute(
                text("SELECT * FROM campaigns ORDER BY created_at DESC")
            )
            campaigns = []
            for row in rows.mappings():
                campaign = self._row_to_campaign_dict(row)
                # Загружаем recipients
                recs = await conn.execute(
                    text("SELECT * FROM recipients WHERE campaign_id=:cid"),
                    {"cid": row["campaign_id"]},
                )
                recipients = []
                for r in recs.mappings():
                    rd = self._row_to_recipient_dict(r)
                    # Загружаем messages
                    msgs = await conn.execute(
                        text(
                            "SELECT role, content FROM messages WHERE recipient_id=:rid ORDER BY id"
                        ),
                        {"rid": r["id"]},
                    )
                    rd["conversation_history"] = [
                        {"role": m["role"], "content": m["content"]}
                        for m in msgs.mappings()
                    ]
                    recipients.append(rd)
                campaign["recipients"] = recipients
                campaigns.append(campaign)
            return campaigns

    async def get_campaign(self, campaign_id: str) -> dict | None:
        """Одна кампания по ID."""
        async with self._engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT * FROM campaigns WHERE campaign_id=:cid OR campaign_id=:cid2 LIMIT 1"
                ),
                {"cid": campaign_id, "cid2": campaign_id},
            )
            row = result.mappings().first()
            if not row:
                return None

            campaign = self._row_to_campaign_dict(row)

            recs = await conn.execute(
                text("SELECT * FROM recipients WHERE campaign_id=:cid"),
                {"cid": row["campaign_id"]},
            )
            recipients = []
            for r in recs.mappings():
                rd = self._row_to_recipient_dict(r)
                msgs = await conn.execute(
                    text(
                        "SELECT role, content FROM messages WHERE recipient_id=:rid ORDER BY id"
                    ),
                    {"rid": r["id"]},
                )
                rd["conversation_history"] = [
                    {"role": m["role"], "content": m["content"]}
                    for m in msgs.mappings()
                ]
                recipients.append(rd)
            campaign["recipients"] = recipients
            return campaign

    async def get_all_recipients(self) -> list[tuple[str, dict]]:
        """Все recipients из всех кампаний."""
        async with self._engine.connect() as conn:
            recs = await conn.execute(
                text("SELECT * FROM recipients ORDER BY last_message_at DESC")
            )
            results = []
            for r in recs.mappings():
                rd = self._row_to_recipient_dict(r)
                msgs = await conn.execute(
                    text(
                        "SELECT role, content FROM messages WHERE recipient_id=:rid ORDER BY id"
                    ),
                    {"rid": r["id"]},
                )
                rd["conversation_history"] = [
                    {"role": m["role"], "content": m["content"]}
                    for m in msgs.mappings()
                ]
                results.append((r["campaign_id"], rd))
            return results

    # ── Кеш скраппера (остаётся JSON) ──

    def get_scraper_cache_list(self) -> list[dict]:
        results: list[dict] = []
        if not self.cache_dir.exists():
            return results
        for path in sorted(self.cache_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                companies = data.get("companies", [])
                results.append({
                    "query": data.get("query", path.stem),
                    "companies_count": len(companies),
                    "from_twogis": data.get("from_twogis", 0),
                    "from_yandex": data.get("from_yandex", 0),
                    "duplicates_removed": data.get("duplicates_removed", 0),
                    "file_size_kb": round(path.stat().st_size / 1024, 1),
                    "file_name": path.name,
                })
            except Exception:
                pass
        return results

    def get_scraper_cache(self, file_name: str) -> dict | None:
        path = self.cache_dir / file_name
        if not path.exists():
            for p in self.cache_dir.glob("*.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if data.get("query") == file_name:
                        return data
                except Exception:
                    pass
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    # ── Аккаунты ──

    async def get_accounts(self) -> list[dict]:
        """Аккаунты из DB (маскированные)."""
        async with self._engine.connect() as conn:
            rows = await conn.execute(text("SELECT * FROM accounts"))
            result = []
            for row in rows.mappings():
                phone = row["phone"]
                masked = (
                    phone[:4] + "***" + phone[-4:]
                    if len(phone) > 8
                    else "***"
                )
                result.append({
                    "phone_masked": masked,
                    "active": bool(row["active"]),
                    "session_name": row["session_name"],
                })
            return result

    # ── Утилиты (для совместимости) ──

    def get_outreach_mtimes(self) -> dict[str, float]:
        """Не используется с DB, но нужен для совместимости."""
        return {}

    # ── Конвертеры ──

    @staticmethod
    def _row_to_campaign_dict(row) -> dict:
        return {
            "campaign_id": row["campaign_id"],
            "user_id": row["user_id"],
            "name": row["name"] or "",
            "offer": row["offer"] or "",
            "status": row["status"] or "pending",
            "sent_count": row["sent_count"] or 0,
            "warm_count": row["warm_count"] or 0,
            "rejected_count": row["rejected_count"] or 0,
            "not_found_count": row["not_found_count"] or 0,
            "manager_ids": json.loads(row["manager_ids"] or "[]"),
            "system_prompt": row["system_prompt"] or "",
            "service_info": row["service_info"] or "",
            "work_hour_start": row["work_hour_start"],
            "work_hour_end": row["work_hour_end"],
            "recipients": [],
        }

    @staticmethod
    def _row_to_recipient_dict(row) -> dict:
        return {
            "phone": row["phone"],
            "company_name": row["company_name"] or "",
            "contact_name": row["contact_name"],
            "category": row["category"],
            "rating": row["rating"],
            "reviews_count": row["reviews_count"],
            "website": row["website"],
            "working_hours": row["working_hours"],
            "address": row["address"],
            "director_name": row["director_name"],
            "telegram_user_id": row["telegram_user_id"],
            "account_phone": row["account_phone"],
            "referral_context": row["referral_context"],
            "status": row["status"] or "pending",
            "last_message_at": row["last_message_at"],
            "ping_count": row["ping_count"] or 0,
            "error_message": row["error_message"],
            "conversation_history": [],
        }
