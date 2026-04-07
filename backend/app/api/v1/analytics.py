"""Analytics API — aggregated stats for a seller."""

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_seller
from app.database import get_db
from app.models.gift import GiftLog
from app.models.message import MessageLog
from app.models.seller import Seller
from app.models.session import LiveSession
from app.schemas.analytics import AnalyticsResponse
from app.schemas.gift import GiftBreakdown, GiftStats, TopGifter

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    start_date: date | None = Query(
        default=None, description="Filter sessions from this date (inclusive)"
    ),
    end_date: date | None = Query(
        default=None, description="Filter sessions until this date (inclusive)"
    ),
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
):
    seller_id = current_seller.id

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

    sentiment_rows = await db.execute(
        select(MessageLog.sentiment, func.count(MessageLog.id))
        .where(MessageLog.session_id.in_(session_subquery))
        .group_by(MessageLog.sentiment)
    )
    sentiment_breakdown = {row[0]: row[1] for row in sentiment_rows.all()}

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

    # Gift stats
    gift_session_subquery = select(LiveSession.id).where(session_filter).scalar_subquery()

    total_gifts = (
        await db.scalar(
            select(func.count(GiftLog.id)).where(GiftLog.session_id.in_(gift_session_subquery))
        )
        or 0
    )

    total_diamonds = (
        await db.scalar(
            select(func.coalesce(func.sum(GiftLog.total_diamonds), 0)).where(
                GiftLog.session_id.in_(gift_session_subquery)
            )
        )
        or 0
    )

    total_gift_usd = (
        await db.scalar(
            select(func.coalesce(func.sum(GiftLog.estimated_usd), 0.0)).where(
                GiftLog.session_id.in_(gift_session_subquery)
            )
        )
        or 0.0
    )

    # Top gifters (top 5 by total diamonds)
    top_gifter_rows = await db.execute(
        select(
            GiftLog.user_unique_id,
            func.sum(GiftLog.total_diamonds).label("sum_diamonds"),
            func.count(GiftLog.id).label("gift_count"),
        )
        .where(GiftLog.session_id.in_(gift_session_subquery))
        .group_by(GiftLog.user_unique_id)
        .order_by(func.sum(GiftLog.total_diamonds).desc())
        .limit(5)
    )
    top_gifters = [
        TopGifter(user=row[0], total_diamonds=int(row[1]), gift_count=int(row[2]))
        for row in top_gifter_rows.all()
    ]

    # Gift breakdown by gift type
    gift_breakdown_rows = await db.execute(
        select(
            GiftLog.gift_name,
            func.count(GiftLog.id).label("count"),
            func.sum(GiftLog.total_diamonds).label("sum_diamonds"),
        )
        .where(GiftLog.session_id.in_(gift_session_subquery))
        .group_by(GiftLog.gift_name)
        .order_by(func.sum(GiftLog.total_diamonds).desc())
    )
    gift_breakdown = [
        GiftBreakdown(gift_name=row[0], count=int(row[1]), total_diamonds=int(row[2]))
        for row in gift_breakdown_rows.all()
    ]

    gift_stats = GiftStats(
        total_gifts=total_gifts,
        total_diamonds=int(total_diamonds),
        estimated_usd=float(total_gift_usd),
        top_gifters=top_gifters,
        gift_breakdown=gift_breakdown,
    )

    return AnalyticsResponse(
        total_sessions=total_sessions,
        total_comments=total_comments,
        total_replies=total_replies,
        reply_rate=reply_rate,
        intent_breakdown=intent_breakdown,
        sentiment_breakdown=sentiment_breakdown,
        unanswered_count=unanswered_count,
        gift_stats=gift_stats,
    )
