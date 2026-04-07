"""Live Session API — start/stop/status/history + full RAG wiring."""

import asyncio
import functools
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_seller
from TikTokLive.client.client import TikTokLiveClient

from app.api.ws import broadcast
from app.core.ai.factory import get_embed_provider, get_reply_provider
from app.core.crypto import decrypt
from app.core.rag import retriever
from app.core.rag.pipeline import RAGPipeline
from app.core.session_state import get_session_state
from app.core.tiktok.listener import LiveListener
from app.core.tiktok.replier import Replier
from app.database import get_db, get_session_factory
from app.models.message import MessageLog
from app.models.seller import Seller
from app.models.session import LiveSession, SessionStatus
from app.schemas.session import (
    MessageLogResponse,
    SessionResponse,
    SessionStatusResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


# ── Internal helpers ─────────────────────────────────────────────────────────


def _build_pipeline(seller: Seller) -> RAGPipeline:
    embed_provider = get_embed_provider()
    reply_provider = get_reply_provider()

    async def _fetch_overrides(seller_id: str) -> list[tuple[str, str]]:
        """Placeholder: return empty list until override storage is implemented."""
        return []

    return RAGPipeline(
        seller_id=seller.id,
        seller_settings=seller.bot_settings,
        embed_fn=embed_provider.embed,
        retrieve_fn=retriever.query,
        generate_reply_fn=reply_provider.generate_reply,
        fetch_overrides_fn=_fetch_overrides,
    )


async def _handle_comment(seller_id: str, user: str, text: str) -> None:
    """Background callback: filter → RAG → save → reply → broadcast.

    Note: seller_id is bound via functools.partial when registering the callback.
    """
    state = get_session_state(seller_id)

    if state.bot_paused or state.active_pipeline is None or state.active_session_id is None:
        return

    max_replies = state.active_pipeline.seller_settings.get("max_replies_per_session", 500)
    if state.reply_count >= max_replies:
        logger.info("max_replies_per_session reached (%d), skipping", max_replies)
        return

    # Save incoming comment
    message_id: str | None = None
    async with get_session_factory()() as db:
        msg = MessageLog(
            session_id=state.active_session_id,
            user_unique_id=user,
            comment=text,
            intent="unknown",
            chunks_used=[],
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        message_id = msg.id

    # Broadcast comment to dashboard (with seller_id for routing)
    await broadcast(
        {
            "type": "comment",
            "seller_id": seller_id,
            "message_id": message_id,
            "user": user,
            "content": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    # Run RAG pipeline
    result = await state.active_pipeline.process(user, text)

    if result.skipped or result.reply is None:
        async with get_session_factory()() as db:
            msg = await db.get(MessageLog, message_id)
            if msg:
                msg.intent = result.intent
                await db.commit()
        return

    # Send reply via replier (with throttle)
    try:
        if state.active_replier is not None:
            await state.active_replier.send(result.reply)
        state.reply_count += 1
    except Exception:
        logger.exception("Failed to send TikTok reply")

    # Persist reply
    async with get_session_factory()() as db:
        msg = await db.get(MessageLog, message_id)
        if msg:
            msg.reply = result.reply
            msg.intent = result.intent
            msg.chunks_used = result.chunks_used
            await db.commit()

    # Broadcast reply to dashboard (with seller_id for routing)
    await broadcast(
        {
            "type": "reply",
            "seller_id": seller_id,
            "message_id": message_id,
            "content": result.reply,
            "intent": result.intent,
            "chunks_used": result.chunks_used,
        }
    )


async def _handle_disconnect(seller_id: str) -> None:
    """Callback when TikTok stream ends or connection drops.

    Note: seller_id is bound via functools.partial when registering the callback.
    """
    state = get_session_state(seller_id)

    logger.info("TikTok disconnect for seller %s — marking session ended", seller_id)
    if state.active_session_id:
        async with get_session_factory()() as db:
            session = await db.get(LiveSession, state.active_session_id)
            if session:
                session.status = SessionStatus.ENDED
                session.ended_at = datetime.now(timezone.utc)
                await db.commit()

    await broadcast({"type": "status", "seller_id": seller_id, "connected": False})

    state.reset()


# ── API Endpoints ─────────────────────────────────────────────────────────────


@router.post("/start", response_model=SessionStatusResponse)
async def start_session(
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
) -> SessionStatusResponse:
    seller_id = current_seller.id
    state = get_session_state(seller_id)

    if state.active_session_id is not None:
        raise HTTPException(status_code=400, detail="A session is already active. Stop it first.")

    # Decrypt TikTok credentials
    session_id = decrypt(current_seller.tiktok_session_id_encrypted)
    target_idc = decrypt(current_seller.tiktok_target_idc_encrypted)

    # Build TikTok client
    tiktok_client = TikTokLiveClient(unique_id=current_seller.tiktok_unique_id)
    tiktok_client.web.set_session(session_id, target_idc)

    # Build components
    listener = LiveListener(tiktok_client)
    replier = Replier(
        web_client=tiktok_client.web,
        delay_min=float(current_seller.bot_settings.get("reply_delay_min", 5)),
        delay_max=float(current_seller.bot_settings.get("reply_delay_max", 15)),
    )
    pipeline = _build_pipeline(current_seller)

    # Register callbacks with seller_id bound via partial
    listener.on_comment(functools.partial(_handle_comment, seller_id))
    listener.on_disconnect(functools.partial(_handle_disconnect, seller_id))

    # Create DB session record
    live_session = LiveSession(seller_id=seller_id, status=SessionStatus.ACTIVE)
    db.add(live_session)
    await db.commit()
    await db.refresh(live_session)

    # Store state
    state.active_session_id = live_session.id
    state.active_listener = listener
    state.active_replier = replier
    state.active_pipeline = pipeline
    state.bot_paused = False
    state.reply_count = 0

    # Start listener in background (non-blocking)
    task = asyncio.create_task(listener.start(), name=f"tiktok-listener-{seller_id}")
    task.add_done_callback(
        lambda t: (
            logger.exception(
                "Listener task crashed for seller %s", seller_id, exc_info=t.exception()
            )
            if not t.cancelled() and t.exception()
            else None
        )
    )
    state.active_task = task

    await broadcast({"type": "status", "seller_id": seller_id, "connected": True, "room_id": None})
    logger.info("Session started for seller %s: %s", seller_id, live_session.id)

    return SessionStatusResponse(
        connected=True, session=SessionResponse.model_validate(live_session)
    )


@router.post("/stop")
async def stop_session(
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
) -> dict[str, str]:
    seller_id = current_seller.id
    state = get_session_state(seller_id)

    if state.active_session_id is None:
        raise HTTPException(status_code=400, detail="No active session")

    if state.active_task is not None and not state.active_task.done():
        state.active_task.cancel()

    if state.active_listener is not None:
        try:
            await state.active_listener.stop()
        except Exception:
            logger.exception("Error stopping listener for seller %s", seller_id)

    session = await db.get(LiveSession, state.active_session_id)
    if session:
        session.status = SessionStatus.ENDED
        session.ended_at = datetime.now(timezone.utc)
        await db.commit()

    state.reset()

    await broadcast({"type": "status", "seller_id": seller_id, "connected": False})
    return {"message": "Session stopped"}


@router.get("/status", response_model=SessionStatusResponse)
async def get_status(
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
) -> SessionStatusResponse:
    seller_id = current_seller.id
    state = get_session_state(seller_id)

    if state.active_session_id is None:
        return SessionStatusResponse(connected=False, session=None)

    result = await db.execute(select(LiveSession).where(LiveSession.id == state.active_session_id))
    session = result.scalar_one_or_none()
    if session is None or session.status != SessionStatus.ACTIVE:
        return SessionStatusResponse(connected=False, session=None)

    return SessionStatusResponse(connected=True, session=SessionResponse.model_validate(session))


@router.get("/history", response_model=list[SessionResponse])
async def get_history(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
) -> list[SessionResponse]:
    seller_id = current_seller.id
    offset = (page - 1) * limit
    result = await db.execute(
        select(LiveSession)
        .where(LiveSession.seller_id == seller_id)
        .order_by(LiveSession.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    sessions = result.scalars().all()
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get("/{session_id}/messages", response_model=list[MessageLogResponse])
async def get_session_messages(
    session_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
) -> list[MessageLogResponse]:
    session = await db.get(LiveSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Ownership check: seller can only view their own session messages
    if session.seller_id != current_seller.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this session")

    offset = (page - 1) * limit
    result = await db.execute(
        select(MessageLog)
        .where(MessageLog.session_id == session_id)
        .order_by(MessageLog.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return [MessageLogResponse.model_validate(m) for m in result.scalars().all()]
