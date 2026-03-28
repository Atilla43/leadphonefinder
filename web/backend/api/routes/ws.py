"""WebSocket эндпоинт для real-time обновлений."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws/events")
async def websocket_events(websocket: WebSocket) -> None:
    """WebSocket для real-time событий.

    Клиент может отправлять:
      {"type": "ping"}
      {"type": "subscribe", "channels": ["campaigns", "conversations"]}

    Сервер отправляет:
      {"type": "pong"}
      {"type": "campaign_updated", "data": {...}}
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            # subscribe/unsubscribe можно расширить позже
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
