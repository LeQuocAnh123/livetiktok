"""Analytics API — aggregated stats for a seller."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.message import MessageLog
from app.models.seller import Seller
from app.models.session import LiveSession
from app.schemas.analytics import AnalyticsResponse

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(seller_id: str, db: AsyncSession = Depends(get_db)):
    seller = await db.get(Seller, seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")

    total_sessions = await db.scalar(
        select(func.count(LiveSession.id)).where(LiveSession.seller_id == seller_id)
    ) or 0

    session_ids_result = await db.execute(
        select(LiveSession.id).where(LiveSession.seller_id == seller_id)
    )
    session_ids = [row[0] for row in session_ids_result.all()]

    if not session_ids:
        return AnalyticsResponse(
            total_sessions=0,
            total_comments=0,
            total_replies=0,
            reply_rate=0.0,
            intent_breakdown={},
            unanswered_count=0,
        )

    total_comments = await db.scalar(
        select(func.count(MessageLog.id)).where(MessageLog.session_id.in_(session_ids))
    ) or 0

    total_replies = await db.scalar(
        select(func.count(MessageLog.id)).where(
            MessageLog.session_id.in_(session_ids),
            MessageLog.reply.isnot(None),
        )
    ) or 0

    reply_rate = round((total_replies / total_comments * 100), 1) if total_comments > 0 else 0.0

    intent_rows = await db.execute(
        select(MessageLog.intent, func.count(MessageLog.id))
        .where(MessageLog.session_id.in_(session_ids))
        .group_by(MessageLog.intent)
    )
    intent_breakdown = {row[0]: row[1] for row in intent_rows.all()}

    unanswered_count = await db.scalar(
        select(func.count(MessageLog.id)).where(
            MessageLog.session_id.in_(session_ids),
            MessageLog.reply.is_(None),
            MessageLog.intent.notin_(["skipped", "blacklist"]),
        )
    ) or 0

    return AnalyticsResponse(
        total_sessions=total_sessions,
        total_comments=total_comments,
        total_replies=total_replies,
        reply_rate=reply_rate,
        intent_breakdown=intent_breakdown,
        unanswered_count=unanswered_count,
    )
