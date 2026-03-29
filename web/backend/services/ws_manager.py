"""WebSocket менеджер для real-time обновлений.

Уведомления приходят через DbOutreachStorage.save() → notify_campaign_saved().
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Управляет WebSocket соединениями и рассылкой событий."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WS connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WS disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Рассылает событие всем подключённым клиентам."""
        message = json.dumps(event, ensure_ascii=False)
        disconnected: list[WebSocket] = []
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

    async def start_file_watcher(self, outreach_dir, interval: float = 3.0) -> None:
        """No-op: уведомления идут через DB callback."""
        logger.info("File watcher disabled — using DB save callback for WS notifications")

    def stop_file_watcher(self) -> None:
        """No-op."""
        pass

    def notify_campaign_saved(self, campaign) -> None:
        """Вызывается из DbOutreachStorage.save() (sync контекст).

        Ставит broadcast в очередь event loop.
        """
        if not self.active_connections:
            return
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.broadcast({
                    "type": "campaign_updated",
                    "data": {
                        "campaign_id": campaign.campaign_id,
                        "status": campaign.status,
                        "sent_count": campaign.sent_count,
                        "warm_count": campaign.warm_count,
                        "rejected_count": campaign.rejected_count,
                        "recipients_total": len(campaign.recipients),
                    },
                }))
        except RuntimeError:
            pass  # no event loop — skip notification


# Глобальный singleton
ws_manager = ConnectionManager()
