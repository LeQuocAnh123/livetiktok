"""Analytics API — aggregated stats for a seller."""

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.message import MessageLog
from app.models.seller import Seller
from app.models.session import LiveSession
from app.schemas.analytics import AnalyticsResponse

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    seller_id: str,
    start_date: date | None = Query(
        default=None, description="Filter sessions from this date (inclusive)"
    ),
    end_date: date | None = Query(
        default=None, description="Filter sessions until this date (inclusive)"
    ),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    seller = await db.get(Seller, seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")

    # Base session filter
    session_filter = LiveSession.seller_id == seller_id

    # Add date filters if provided
    if start_date:
        start_datetime = datetime.combine(start_date, time.min)
        session_filter = session_filter & (LiveSession.started_at >= start_datetime)
    if end_date:
        end_datetime = datetime.combine(end_date, time.max)
        session_filter = session_filter & (LiveSession.started_at <= end_datetime)

    total_sessions = await db.scalar(select(func.count(LiveSession.id)).where(session_filter)) or 0

    session_subquery = select(LiveSession.id).where(session_filter).scalar_subquery()

    total_comments = (
        await db.scalar(
            select(func.count(MessageLog.id)).where(MessageLog.session_id.in_(session_subquery))
        )
        or 0
    )

    total_replies = (
        await db.scalar(
            select(func.count(MessageLog.id)).where(
                MessageLog.session_id.in_(session_subquery),
                MessageLog.reply.isnot(None),
            )
        )
        or 0
    )

    reply_rate = round((total_replies / total_comments * 100), 1) if total_comments > 0 else 0.0

    intent_rows = await db.execute(
        select(MessageLog.intent, func.count(MessageLog.id))
        .where(MessageLog.session_id.in_(session_subquery))
        .group_by(MessageLog.intent)
    )
    intent_breakdown = {row[0]: row[1] for row in intent_rows.all()}

    unanswered_count = (
        await db.scalar(
            select(func.count(MessageLog.id)).where(
                MessageLog.session_id.in_(session_subquery),
                MessageLog.reply.is_(None),
                MessageLog.intent.notin_(["skipped", "blacklist"]),
            )
        )
        or 0
    )

    return AnalyticsResponse(
        total_sessions=total_sessions,
        total_comments=total_comments,
        total_replies=total_replies,
        reply_rate=reply_rate,
        intent_breakdown=intent_breakdown,
        unanswered_count=unanswered_count,
    )
