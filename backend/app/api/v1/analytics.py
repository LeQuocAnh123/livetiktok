"""Analytics API — aggregated stats for a seller."""

from collections import Counter
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_seller
from app.core.analytics.keywords import extract_keywords
from app.core.analytics.timeline import compute_timeline
from app.database import get_db
from app.models.gift import GiftLog
from app.models.message import MessageLog
from app.models.seller import Seller
from app.models.session import LiveSession
from app.schemas.analytics import (
    AnalyticsResponse,
    EngagementMetrics,
    KeywordEntry,
    SentimentTrendEntry,
    SessionAnalyticsResponse,
    SessionInfo,
    SessionListEntry,
    SessionSummary,
    TimelineBucketSchema,
)
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

    # ── NEW: Sentiment trend (daily aggregation) ──────────────────────────────
    sentiment_trend_rows = await db.execute(
        select(
            func.strftime("%Y-%m-%d", MessageLog.created_at).label("day"),
            MessageLog.sentiment,
            func.count(MessageLog.id),
        )
        .where(MessageLog.session_id.in_(session_subquery))
        .group_by("day", MessageLog.sentiment)
        .order_by("day")
    )

    trend_map: dict[str, dict[str, int]] = {}
    for day_str, sentiment, cnt in sentiment_trend_rows.all():
        if day_str not in trend_map:
            trend_map[day_str] = {"positive": 0, "neutral": 0, "negative": 0}
        if sentiment in trend_map[day_str]:
            trend_map[day_str][sentiment] = cnt

    sentiment_trend = [
        SentimentTrendEntry(date=d, **counts) for d, counts in sorted(trend_map.items())
    ]

    # ── NEW: Top keywords overall ─────────────────────────────────────────────
    comment_rows = await db.execute(
        select(MessageLog.comment).where(MessageLog.session_id.in_(session_subquery))
    )
    all_comments = [row[0] for row in comment_rows.all()]
    kw_results = extract_keywords(all_comments, top_n=20)
    top_keywords_overall = [KeywordEntry(**kw) for kw in kw_results]

    # ── NEW: Session list (per-session summaries) ─────────────────────────────
    sessions_result = await db.execute(
        select(LiveSession).where(session_filter).order_by(LiveSession.started_at.desc())
    )
    sessions = sessions_result.scalars().all()

    session_list: list[SessionListEntry] = []
    for sess in sessions:
        s_msg_rows = await db.execute(
            select(
                func.count(MessageLog.id),
                func.count(MessageLog.reply),
            ).where(MessageLog.session_id == sess.id)
        )
        s_msg = s_msg_rows.one()
        s_comment_count = s_msg[0]
        s_reply_count = s_msg[1]

        s_intent_rows = await db.execute(
            select(MessageLog.intent, func.count(MessageLog.id))
            .where(MessageLog.session_id == sess.id)
            .group_by(MessageLog.intent)
            .order_by(func.count(MessageLog.id).desc())
            .limit(1)
        )
        s_top_intent_row = s_intent_rows.first()
        s_top_intent = s_top_intent_row[0] if s_top_intent_row else "none"

        s_gift_rows = await db.execute(
            select(
                func.count(GiftLog.id),
                func.coalesce(func.sum(GiftLog.total_diamonds), 0),
            ).where(GiftLog.session_id == sess.id)
        )
        s_gift = s_gift_rows.one()

        duration_minutes = 0.0
        if sess.ended_at and sess.started_at:
            duration_minutes = round((sess.ended_at - sess.started_at).total_seconds() / 60, 1)

        s_reply_rate = (
            round(s_reply_count / s_comment_count * 100, 1) if s_comment_count > 0 else 0.0
        )

        session_list.append(
            SessionListEntry(
                id=sess.id,
                started_at=sess.started_at,
                ended_at=sess.ended_at,
                duration_minutes=duration_minutes,
                comment_count=s_comment_count,
                reply_count=s_reply_count,
                reply_rate=s_reply_rate,
                gift_count=s_gift[0],
                gift_diamonds=int(s_gift[1]),
                top_intent=s_top_intent,
            )
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
        sentiment_trend=sentiment_trend,
        top_keywords_overall=top_keywords_overall,
        session_list=session_list,
    )


@router.get("/sessions/{session_id}", response_model=SessionAnalyticsResponse)
async def get_session_analytics(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
):
    """Get detailed analytics for a single live session."""
    # 1. Fetch session and verify ownership
    session = await db.get(LiveSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.seller_id != current_seller.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # 2. Fetch all messages for this session
    msg_result = await db.execute(select(MessageLog).where(MessageLog.session_id == session_id))
    messages = msg_result.scalars().all()

    # 3. Fetch all gifts for this session
    gift_result = await db.execute(select(GiftLog).where(GiftLog.session_id == session_id))
    gifts = gift_result.scalars().all()

    # 4. Session info
    duration_minutes = 0.0
    if session.ended_at and session.started_at:
        duration_minutes = round((session.ended_at - session.started_at).total_seconds() / 60, 1)

    session_info = SessionInfo(
        id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_minutes=duration_minutes,
    )

    # 5. Summary
    total_comments = len(messages)
    total_replies = sum(1 for m in messages if m.reply is not None)
    reply_rate = round(total_replies / total_comments * 100, 1) if total_comments > 0 else 0.0
    total_gifts_count = len(gifts)
    total_diamonds_sum = sum(g.total_diamonds for g in gifts)
    estimated_usd = round(sum(g.estimated_usd for g in gifts), 2)

    summary = SessionSummary(
        total_comments=total_comments,
        total_replies=total_replies,
        reply_rate=reply_rate,
        total_gifts=total_gifts_count,
        total_diamonds=total_diamonds_sum,
        estimated_usd=estimated_usd,
    )

    # 6. Timeline
    timeline_buckets = compute_timeline(
        session_start=session.started_at,
        session_end=session.ended_at,
        messages=messages,
        gifts=gifts,
        bucket_minutes=5,
    )
    timeline = [
        TimelineBucketSchema(
            bucket_start=b.bucket_start,
            bucket_end=b.bucket_end,
            comment_count=b.comment_count,
            reply_count=b.reply_count,
            gift_count=b.gift_count,
            gift_diamonds=b.gift_diamonds,
        )
        for b in timeline_buckets
    ]

    # 7. Keywords
    comment_texts = [m.comment for m in messages]
    kw_results = extract_keywords(comment_texts, top_n=20)
    top_keywords = [KeywordEntry(**kw) for kw in kw_results]

    # 8. Breakdowns
    intent_counter: dict[str, int] = {}
    sentiment_counter: dict[str, int] = {}
    for m in messages:
        intent_counter[m.intent] = intent_counter.get(m.intent, 0) + 1
        sentiment_counter[m.sentiment] = sentiment_counter.get(m.sentiment, 0) + 1

    # 9. Engagement metrics
    product_inquiry_count = intent_counter.get("product_inquiry", 0)
    product_inquiry_rate = (
        round(product_inquiry_count / total_comments * 100, 1) if total_comments > 0 else 0.0
    )

    unique_commenters = len({m.user_unique_id for m in messages})

    comments_per_minute_avg = 0.0
    if duration_minutes > 0:
        comments_per_minute_avg = round(total_comments / duration_minutes, 1)
    elif total_comments > 0 and messages:
        sorted_msgs = sorted(messages, key=lambda m: m.created_at)
        span = (sorted_msgs[-1].created_at - sorted_msgs[0].created_at).total_seconds() / 60
        if span > 0:
            comments_per_minute_avg = round(total_comments / span, 1)

    # Peak minute
    peak_minute = None
    peak_comments = 0
    if messages:
        minute_counts: Counter[str] = Counter()
        for m in messages:
            minute_key = m.created_at.replace(second=0, microsecond=0).isoformat()
            minute_counts[minute_key] += 1
        if minute_counts:
            peak_key, peak_comments = minute_counts.most_common(1)[0]
            peak_minute = datetime.fromisoformat(peak_key)

    engagement_metrics = EngagementMetrics(
        product_inquiry_rate=product_inquiry_rate,
        unique_commenters=unique_commenters,
        comments_per_minute_avg=comments_per_minute_avg,
        peak_minute=peak_minute,
        peak_comments=peak_comments,
    )

    return SessionAnalyticsResponse(
        session_info=session_info,
        summary=summary,
        timeline=timeline,
        top_keywords=top_keywords,
        intent_breakdown=intent_counter,
        sentiment_breakdown=sentiment_counter,
        engagement_metrics=engagement_metrics,
    )
