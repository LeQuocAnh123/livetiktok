import json
import logging
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

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
async def websocket_monitor(
    websocket: WebSocket,
    token: str = Query(default=""),
):
    required = get_settings().ws_monitor_token
    if required and token != required:
        await websocket.close(code=1008)
        return
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

            msg_type = msg.get("type")
            logger.info("WS command received: %s", msg_type)

            if msg_type == "pause_bot":
                import app.api.v1.sessions as sessions_module
                sessions_module._bot_paused = True
                await broadcast({"type": "status", "paused": True})

            elif msg_type == "resume_bot":
                import app.api.v1.sessions as sessions_module
                sessions_module._bot_paused = False
                await broadcast({"type": "status", "paused": False})

            elif msg_type == "manual_reply":
                await _handle_manual_reply(msg)

    except WebSocketDisconnect:
        if websocket in _connections:
            _connections.remove(websocket)
        logger.info("Dashboard client disconnected (%d remaining)", len(_connections))
    except Exception:
        logger.exception("WebSocket error")
        if websocket in _connections:
            _connections.remove(websocket)


async def _handle_manual_reply(msg: dict) -> None:
    """Send a manual reply for a specific message_id via the active replier."""
    import app.api.v1.sessions as sessions_module
    from app.database import get_session_factory
    from app.models.message import MessageLog

    message_id = msg.get("message_id")
    content = msg.get("content", "").strip()

    if not message_id or not content:
        logger.warning("manual_reply missing message_id or content")
        return

    replier = sessions_module._active_replier
    if replier is None:
        await broadcast({"type": "error", "message": "No active session"})
        return

    try:
        await replier.send(content)
    except Exception as exc:
        logger.exception("manual_reply send failed")
        await broadcast({"type": "error", "message": str(exc)})
        return

    async with get_session_factory()() as db:
        log = await db.get(MessageLog, message_id)
        if log:
            log.reply = content
            log.intent = "manual"
            await db.commit()

    await broadcast({
        "type": "reply",
        "message_id": message_id,
        "content": content,
        "intent": "manual",
        "chunks_used": [],
    })
