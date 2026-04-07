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
from app.core.rag.overrides import get_recent_overrides
from app.core.rag.pipeline import RAGPipeline
from app.core.session_state import get_session_state
from app.core.tiktok.listener import LiveListener
from app.core.tiktok.replier import Replier
from app.database import get_db, get_session_factory
from app.models.message import MessageLog
from app.models.gift import GiftLog
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


def _build_pipeline(seller: Seller, fetch_overrides_fn) -> RAGPipeline:
    embed_provider = get_embed_provider()
    reply_provider = get_reply_provider()
    return RAGPipeline(
        seller_id=seller.id,
        seller_settings=seller.bot_settings,
        embed_fn=embed_provider.embed,
        retrieve_fn=retriever.query,
        generate_reply_fn=reply_provider.generate_reply,
        fetch_overrides_fn=fetch_overrides_fn,
    )


async def _handle_comment(seller_id: str, user: str, text: str) -> None:
    """Background callback: filter → RAG → save → reply → broadcast."""
    state = get_session_state(seller_id)

    if state.bot_paused or state.active_pipeline is None or state.active_session_id is None:
        return

    max_replies = state.active_pipeline.seller_settings.get("max_replies_per_session", 500)
    if state.reply_count >= max_replies:
        logger.info("max_replies_per_session reached (%d), skipping", max_replies)
        return

    # Save incoming comment (intent/sentiment updated after LLM)
    message_id: str | None = None
    async with get_session_factory()() as db:
        msg = MessageLog(
            session_id=state.active_session_id,
            user_unique_id=user,
            comment=text,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        message_id = msg.id

    # Broadcast comment to dashboard
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

    # Run RAG pipeline (now returns intent + sentiment + reply)
    result = await state.active_pipeline.process(user, text)

    # Update message with intent and sentiment regardless of skip
    async with get_session_factory()() as db:
        msg = await db.get(MessageLog, message_id)
        if msg:
            msg.intent = result.intent
            msg.sentiment = result.sentiment
            await db.commit()

    if result.skipped or result.reply is None:
        return

    # Send reply via TikTok
    try:
        if state.active_replier is not None:
            await state.active_replier.send(result.reply)
        state.reply_count += 1
    except Exception:
        logger.exception("Failed to send TikTok reply")
        return

    # Persist reply and chunks to DB
    async with get_session_factory()() as db:
        msg = await db.get(MessageLog, message_id)
        if msg:
            msg.reply = result.reply
            msg.chunks_used = result.chunks_used
            await db.commit()

    # Broadcast reply to dashboard (with sentiment)
    await broadcast(
        {
            "type": "reply",
            "seller_id": seller_id,
            "message_id": message_id,
            "content": result.reply,
            "intent": result.intent,
            "sentiment": result.sentiment,
            "chunks_used": result.chunks_used,
        }
    )

    # Negative sentiment: alert dashboard + bypass cooldown for this user
    if result.sentiment == "negative":
        await broadcast(
            {
                "type": "alert",
                "seller_id": seller_id,
                "severity": "negative",
                "message_id": message_id,
                "comment": text,
                "user": user,
            }
        )
        state.active_pipeline._filter.reset_cooldown(user)


async def _handle_gift(
    seller_id: str, user: str, gift_name: str, diamond_count: int, repeat_count: int
) -> None:
    """Background callback: save gift → broadcast → LLM thank → reply → broadcast."""
    state = get_session_state(seller_id)

    if state.active_session_id is None or state.active_pipeline is None:
        return

    total_diamonds = diamond_count * repeat_count
    estimated_usd = total_diamonds * 0.005

    # 1. Save GiftLog to DB
    gift_log_id: str | None = None
    async with get_session_factory()() as db:
        gift = GiftLog(
            session_id=state.active_session_id,
            user_unique_id=user,
            gift_name=gift_name,
            diamond_count=diamond_count,
            repeat_count=repeat_count,
            total_diamonds=total_diamonds,
            estimated_usd=estimated_usd,
        )
        db.add(gift)
        await db.commit()
        await db.refresh(gift)
        gift_log_id = gift.id

    # 2. Broadcast gift event to dashboard
    await broadcast(
        {
            "type": "gift",
            "seller_id": seller_id,
            "gift_log_id": gift_log_id,
            "user": user,
            "gift_name": gift_name,
            "diamond_count": diamond_count,
            "repeat_count": repeat_count,
            "total_diamonds": total_diamonds,
            "estimated_usd": estimated_usd,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    # 3. Generate LLM thank-you (skip if bot paused or auto_reply disabled)
    auto_reply = state.active_pipeline.seller_settings.get("auto_reply_enabled", True)
    if state.bot_paused or not auto_reply:
        return

    gift_context = (
        f"Viewer {user} vừa tặng {repeat_count}x {gift_name} "
        f"({total_diamonds} diamonds, ~${estimated_usd:.2f})"
    )

    try:
        result = await state.active_pipeline.process_gift(user, gift_context)
    except Exception:
        logger.exception("Failed to generate gift thank-you for %s", user)
        return

    # 4. Send reply via TikTok
    try:
        if state.active_replier is not None:
            await state.active_replier.send(result.reply)
    except Exception:
        logger.exception("Failed to send gift thank-you to TikTok")

    # 5. Update GiftLog with thank_reply
    async with get_session_factory()() as db:
        gift = await db.get(GiftLog, gift_log_id)
        if gift:
            gift.thank_reply = result.reply
            await db.commit()

    # 6. Broadcast gift reply to dashboard
    await broadcast(
        {
            "type": "gift_reply",
            "seller_id": seller_id,
            "gift_log_id": gift_log_id,
            "content": result.reply,
            "user": user,
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

    # Build fetch_overrides_fn bound to seller_id
    async def _fetch_overrides(sid: str) -> list[tuple[str, str]]:
        async with get_session_factory()() as db:
            return await get_recent_overrides(sid, db, limit=5)

    pipeline = _build_pipeline(current_seller, _fetch_overrides)

    # Register callbacks with seller_id bound via partial
    listener.on_comment(functools.partial(_handle_comment, seller_id))
    listener.on_gift(functools.partial(_handle_gift, seller_id))
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
