"""WebSocket endpoint for real-time dashboard updates."""

import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.session_state import get_session_state

logger = logging.getLogger(__name__)
router = APIRouter()

# Connections keyed by seller_id for multi-tenant isolation
_connections: dict[str, list[WebSocket]] = defaultdict(list)


async def broadcast(message: dict[str, Any]) -> None:
    """Send a message to dashboard clients for a specific seller.

    Message must contain 'seller_id' key for routing.
    If no seller_id, broadcasts to all (legacy fallback).
    """
    seller_id = message.get("seller_id")

    if seller_id:
        # Route to specific seller's connections
        dead = []
        for ws in _connections.get(seller_id, []):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in _connections[seller_id]:
                _connections[seller_id].remove(ws)
    else:
        # Fallback: broadcast to all (should not happen in multi-tenant)
        logger.warning("Broadcast without seller_id - sending to all")
        for seller_connections in _connections.values():
            dead = []
            for ws in seller_connections:
                try:
                    await ws.send_text(json.dumps(message))
                except Exception:
                    dead.append(ws)
            for ws in dead:
                seller_connections.remove(ws)


@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    # Auth via cookie
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=1008)
        return

    from app.core.security import decode_access_token

    seller_id = decode_access_token(token)
    if not seller_id:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    _connections[seller_id].append(websocket)
    logger.info(
        "Dashboard client connected: seller=%s (%d connections for this seller)",
        seller_id,
        len(_connections[seller_id]),
    )

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from WS client, ignoring")
                continue

            msg_type = msg.get("type")
            logger.info("WS command received from seller %s: %s", seller_id, msg_type)

            if msg_type == "pause_bot":
                state = get_session_state(seller_id)
                state.bot_paused = True
                await broadcast({"type": "status", "seller_id": seller_id, "paused": True})

            elif msg_type == "resume_bot":
                state = get_session_state(seller_id)
                state.bot_paused = False
                await broadcast({"type": "status", "seller_id": seller_id, "paused": False})

            elif msg_type == "manual_reply":
                await _handle_manual_reply(seller_id, msg)

    except WebSocketDisconnect:
        if websocket in _connections[seller_id]:
            _connections[seller_id].remove(websocket)
        logger.info(
            "Dashboard client disconnected: seller=%s (%d remaining)",
            seller_id,
            len(_connections[seller_id]),
        )
    except Exception:
        logger.exception("WebSocket error")
        if websocket in _connections[seller_id]:
            _connections[seller_id].remove(websocket)


async def _handle_manual_reply(seller_id: str, msg: dict) -> None:
    """Send a manual reply for a specific message_id via the active replier."""
    from app.database import get_session_factory
    from app.models.message import MessageLog

    message_id = msg.get("message_id")
    content = msg.get("content", "").strip()

    if not message_id or not content:
        logger.warning("manual_reply missing message_id or content")
        return

    state = get_session_state(seller_id)
    replier = state.active_replier
    if replier is None:
        await broadcast({"type": "error", "seller_id": seller_id, "message": "No active session"})
        return

    try:
        await replier.send(content)
    except Exception as exc:
        logger.exception("manual_reply send failed")
        await broadcast({"type": "error", "seller_id": seller_id, "message": str(exc)})
        return

    async with get_session_factory()() as db:
        log = await db.get(MessageLog, message_id)
        if log:
            log.reply = content
            log.intent = "manual"
            await db.commit()

    await broadcast(
        {
            "type": "reply",
            "seller_id": seller_id,
            "message_id": message_id,
            "content": content,
            "intent": "manual",
            "chunks_used": [],
        }
    )
