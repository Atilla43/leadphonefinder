"""WebSocket менеджер с file watcher для real-time обновлений."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Управляет WebSocket соединениями и рассылкой событий."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._prev_mtimes: dict[str, float] = {}
        self._watch_task: asyncio.Task | None = None

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

    async def start_file_watcher(
        self, outreach_dir: Path, interval: float = 3.0,
    ) -> None:
        """Запускает polling file watcher на data/outreach/."""
        self._watch_task = asyncio.create_task(
            self._watch_loop(outreach_dir, interval)
        )

    async def _watch_loop(self, outreach_dir: Path, interval: float) -> None:
        """Периодически проверяет изменения файлов кампаний."""
        import os

        while True:
            try:
                await asyncio.sleep(interval)
                if not self.active_connections:
                    continue
                if not outreach_dir.exists():
                    continue

                current_mtimes: dict[str, float] = {}
                for path in outreach_dir.glob("campaign_*.json"):
                    current_mtimes[path.name] = os.path.getmtime(path)

                # Находим изменённые файлы
                changed_files: list[str] = []
                for name, mtime in current_mtimes.items():
                    if name not in self._prev_mtimes or self._prev_mtimes[name] != mtime:
                        changed_files.append(name)

                # Новые файлы
                new_files = set(current_mtimes.keys()) - set(self._prev_mtimes.keys())
                # Удалённые файлы
                deleted_files = set(self._prev_mtimes.keys()) - set(current_mtimes.keys())

                self._prev_mtimes = current_mtimes

                for name in changed_files:
                    path = outreach_dir / name
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                        cid = data.get("campaign_id") or str(data.get("user_id", ""))
                        await self.broadcast({
                            "type": "campaign_updated",
                            "data": {
                                "campaign_id": cid,
                                "status": data.get("status"),
                                "sent_count": data.get("sent_count", 0),
                                "warm_count": data.get("warm_count", 0),
                                "rejected_count": data.get("rejected_count", 0),
                                "recipients_total": len(data.get("recipients", [])),
                            },
                        })
                    except Exception as e:
                        logger.error(f"Error parsing changed file {name}: {e}")

                for name in new_files:
                    if name not in changed_files:
                        await self.broadcast({
                            "type": "campaign_created",
                            "data": {"file": name},
                        })

                for name in deleted_files:
                    await self.broadcast({
                        "type": "campaign_deleted",
                        "data": {"file": name},
                    })

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"File watcher error: {e}")

    def stop_file_watcher(self) -> None:
        if self._watch_task:
            self._watch_task.cancel()
            self._watch_task = None


# Глобальный singleton
ws_manager = ConnectionManager()
