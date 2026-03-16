"""Персистентное хранилище outreach-кампаний (JSON-файлы)."""

import json
import logging
from pathlib import Path
from typing import Optional

from bot.models.outreach import OutreachCampaign

logger = logging.getLogger(__name__)


class OutreachStorage:
    """Сохраняет/загружает кампании в JSON-файлы."""

    STORAGE_DIR = Path("data/outreach")

    def __init__(self) -> None:
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def _path(self, user_id: int, campaign_id: str = "") -> Path:
        if campaign_id:
            return self.STORAGE_DIR / f"campaign_{user_id}_{campaign_id}.json"
        # Обратная совместимость со старым форматом
        return self.STORAGE_DIR / f"campaign_{user_id}.json"

    def save(self, campaign: OutreachCampaign) -> None:
        """Сохраняет кампанию на диск."""
        path = self._path(campaign.user_id, campaign.campaign_id)
        data = campaign.to_dict()
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug(f"Campaign {campaign.campaign_id} saved for user {campaign.user_id}")

    def load(self, user_id: int, campaign_id: str = "") -> Optional[OutreachCampaign]:
        """Загружает кампанию с диска."""
        path = self._path(user_id, campaign_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return OutreachCampaign.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load campaign for user {user_id}: {e}")
            return None

    def delete(self, user_id: int, campaign_id: str = "") -> None:
        """Удаляет файл кампании."""
        path = self._path(user_id, campaign_id)
        if path.exists():
            path.unlink()
            logger.debug(f"Campaign {campaign_id} deleted for user {user_id}")

    def load_all_active(self) -> list[OutreachCampaign]:
        """Загружает все активные кампании."""
        campaigns = []
        for path in self.STORAGE_DIR.glob("campaign_*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                campaign = OutreachCampaign.from_dict(data)
                if campaign.status in ("sending", "listening", "paused"):
                    campaigns.append(campaign)
                else:
                    path.unlink()
            except Exception as e:
                logger.error(f"Failed to load campaign from {path}: {e}")
        return campaigns

    def load_user_campaigns(self, user_id: int) -> list[OutreachCampaign]:
        """Загружает все кампании пользователя."""
        campaigns = []
        for path in self.STORAGE_DIR.glob(f"campaign_{user_id}*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                campaign = OutreachCampaign.from_dict(data)
                if campaign.status in ("sending", "listening", "paused"):
                    campaigns.append(campaign)
            except Exception as e:
                logger.error(f"Failed to load campaign from {path}: {e}")
        return campaigns
