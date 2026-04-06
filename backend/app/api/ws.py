import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

# Broadcast registry — single-seller v1
_connections: list[WebSocket] = []


async def broadcast(message: dict[str, Any]) -> None:
    """Send a message to all connected dashboard clients."""
    dead = []
    for ws in _connections:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.remove(ws)


@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    await websocket.accept()
    _connections.append(websocket)
    logger.info("Dashboard client connected (%d total)", len(_connections))
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from WS client, ignoring")
                continue
            logger.info("WS command received: %s", msg.get("type"))
            # Command handling wired in Plan 2 (RAG pipeline)
    except WebSocketDisconnect:
        if websocket in _connections:
            _connections.remove(websocket)
        logger.info("Dashboard client disconnected (%d remaining)", len(_connections))
    except Exception:
        logger.exception("WebSocket error")
        if websocket in _connections:
            _connections.remove(websocket)
