"""Сервис чтения JSON-данных бота с кешированием по file mtime."""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DataReader:
    """Читает JSON-файлы бота с кешем по mtime."""

    def __init__(
        self,
        outreach_dir: Path,
        cache_dir: Path,
        accounts_file: Path,
        cache_ttl: int = 5,
    ) -> None:
        self.outreach_dir = outreach_dir
        self.cache_dir = cache_dir
        self.accounts_file = accounts_file
        self.cache_ttl = cache_ttl
        # file_path → (mtime, parsed_data)
        self._cache: dict[str, tuple[float, Any]] = {}

    def _read_json(self, path: Path) -> Any | None:
        """Читает JSON с кешированием по mtime."""
        key = str(path)
        try:
            if not path.exists():
                return None
            mtime = os.path.getmtime(path)
            cached = self._cache.get(key)
            if cached and cached[0] == mtime:
                return cached[1]
            data = json.loads(path.read_text(encoding="utf-8"))
            self._cache[key] = (mtime, data)
            return data
        except Exception as e:
            logger.error(f"Error reading {path}: {e}")
            return None

    # ── Кампании ──

    def get_all_campaigns(self) -> list[dict]:
        """Загружает все кампании из data/outreach/."""
        campaigns: list[dict] = []
        if not self.outreach_dir.exists():
            return campaigns
        for path in sorted(self.outreach_dir.glob("campaign_*.json")):
            data = self._read_json(path)
            if data:
                campaigns.append(data)
        return campaigns

    def get_campaign(self, campaign_id: str) -> dict | None:
        """Ищет кампанию по campaign_id."""
        for campaign in self.get_all_campaigns():
            cid = campaign.get("campaign_id") or ""
            uid = str(campaign.get("user_id", ""))
            # Поддержка старого формата (campaign_id=None)
            if cid == campaign_id or uid == campaign_id:
                return campaign
        return None

    def get_all_recipients(self) -> list[tuple[str, dict]]:
        """Все recipients из всех кампаний. Возвращает (campaign_id, recipient)."""
        results: list[tuple[str, dict]] = []
        for campaign in self.get_all_campaigns():
            cid = campaign.get("campaign_id") or str(campaign.get("user_id", ""))
            for r in campaign.get("recipients", []):
                results.append((cid, r))
        return results

    # ── Кеш скраппера ──

    def get_scraper_cache_list(self) -> list[dict]:
        """Список кешированных запросов."""
        results: list[dict] = []
        if not self.cache_dir.exists():
            return results
        for path in sorted(self.cache_dir.glob("*.json")):
            data = self._read_json(path)
            if not data:
                continue
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
        return results

    def get_scraper_cache(self, file_name: str) -> dict | None:
        """Данные конкретного кеша скраппера."""
        path = self.cache_dir / file_name
        if not path.exists():
            # Поиск по query
            for p in self.cache_dir.glob("*.json"):
                data = self._read_json(p)
                if data and data.get("query") == file_name:
                    return data
            return None
        return self._read_json(path)

    # ── Аккаунты ──

    def get_accounts(self) -> list[dict]:
        """Загружает аккаунты (маскирует секреты)."""
        data = self._read_json(self.accounts_file)
        if not data or not isinstance(data, list):
            return []
        result: list[dict] = []
        for account in data:
            phone = account.get("phone", "")
            masked = phone[:4] + "***" + phone[-4:] if len(phone) > 8 else "***"
            result.append({
                "phone_masked": masked,
                "active": account.get("active", True),
                "session_name": account.get("session_name", ""),
            })
        return result

    # ── Утилиты для mtimes (WebSocket) ──

    def get_outreach_mtimes(self) -> dict[str, float]:
        """Возвращает {filename: mtime} для всех файлов кампаний."""
        mtimes: dict[str, float] = {}
        if not self.outreach_dir.exists():
            return mtimes
        for path in self.outreach_dir.glob("campaign_*.json"):
            mtimes[path.name] = os.path.getmtime(path)
        return mtimes
