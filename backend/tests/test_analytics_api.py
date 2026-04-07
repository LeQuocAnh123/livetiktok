"""Integration tests for Analytics API."""

import pytest
from httpx import AsyncClient


async def test_analytics_returns_zeros_for_new_seller(auth_client: AsyncClient, test_seller):
    """GET /api/v1/analytics/ returns zero stats for authenticated seller with no data."""
    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 0
    assert data["total_comments"] == 0
    assert data["total_replies"] == 0
    assert data["reply_rate"] == 0.0
    assert data["intent_breakdown"] == {}
    assert data["sentiment_breakdown"] == {}
    assert data["unanswered_count"] == 0


async def test_unauthenticated_returns_401(client: AsyncClient):
    """Unauthenticated requests return 401."""
    resp = await client.get("/api/v1/analytics/")
    assert resp.status_code == 401


from datetime import datetime, timedelta
from app.models.session import LiveSession
from app.models.message import MessageLog
from app.models.gift import GiftLog


async def test_overview_includes_sentiment_trend(auth_client: AsyncClient, db_session, test_seller):
    """Enhanced overview returns sentiment_trend as daily aggregation."""
    session = LiveSession(
        id="sess-trend-1",
        seller_id=test_seller.id,
        started_at=datetime(2026, 1, 1, 10, 0),
        ended_at=datetime(2026, 1, 1, 12, 0),
    )
    db_session.add(session)

    msgs = [
        MessageLog(
            id="mt1",
            session_id="sess-trend-1",
            user_unique_id="u1",
            comment="great",
            reply="thanks",
            intent="greeting",
            sentiment="positive",
            created_at=datetime(2026, 1, 1, 10, 5),
        ),
        MessageLog(
            id="mt2",
            session_id="sess-trend-1",
            user_unique_id="u2",
            comment="ok",
            reply="hi",
            intent="greeting",
            sentiment="neutral",
            created_at=datetime(2026, 1, 1, 10, 10),
        ),
        MessageLog(
            id="mt3",
            session_id="sess-trend-1",
            user_unique_id="u3",
            comment="bad",
            reply="sorry",
            intent="unknown",
            sentiment="negative",
            created_at=datetime(2026, 1, 1, 10, 15),
        ),
    ]
    db_session.add_all(msgs)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()

    assert "sentiment_trend" in data
    assert len(data["sentiment_trend"]) == 1
    day = data["sentiment_trend"][0]
    assert day["date"] == "2026-01-01"
    assert day["positive"] == 1
    assert day["neutral"] == 1
    assert day["negative"] == 1


async def test_overview_includes_top_keywords(auth_client: AsyncClient, db_session, test_seller):
    """Enhanced overview returns top_keywords_overall."""
    session = LiveSession(
        id="sess-kw-1",
        seller_id=test_seller.id,
        started_at=datetime(2026, 1, 1, 10, 0),
        ended_at=datetime(2026, 1, 1, 12, 0),
    )
    db_session.add(session)

    msgs = [
        MessageLog(
            id="mk1",
            session_id="sess-kw-1",
            user_unique_id="u1",
            comment="giá bao nhiêu",
            reply="100k",
            intent="product_inquiry",
            sentiment="neutral",
            created_at=datetime(2026, 1, 1, 10, 5),
        ),
        MessageLog(
            id="mk2",
            session_id="sess-kw-1",
            user_unique_id="u2",
            comment="giá sản phẩm",
            reply="200k",
            intent="product_inquiry",
            sentiment="neutral",
            created_at=datetime(2026, 1, 1, 10, 10),
        ),
    ]
    db_session.add_all(msgs)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()

    assert "top_keywords_overall" in data
    assert len(data["top_keywords_overall"]) > 0
    words = [kw["word"] for kw in data["top_keywords_overall"]]
    assert "giá" in words


async def test_overview_includes_session_list(auth_client: AsyncClient, db_session, test_seller):
    """Enhanced overview returns session_list with per-session summaries."""
    session = LiveSession(
        id="sess-list-1",
        seller_id=test_seller.id,
        started_at=datetime(2026, 1, 1, 10, 0),
        ended_at=datetime(2026, 1, 1, 11, 30),
    )
    db_session.add(session)

    msgs = [
        MessageLog(
            id="ml1",
            session_id="sess-list-1",
            user_unique_id="u1",
            comment="giá bao nhiêu",
            reply="100k",
            intent="product_inquiry",
            sentiment="positive",
            created_at=datetime(2026, 1, 1, 10, 5),
        ),
        MessageLog(
            id="ml2",
            session_id="sess-list-1",
            user_unique_id="u2",
            comment="chào shop",
            reply=None,
            intent="greeting",
            sentiment="neutral",
            created_at=datetime(2026, 1, 1, 10, 10),
        ),
        MessageLog(
            id="ml3",
            session_id="sess-list-1",
            user_unique_id="u3",
            comment="sản phẩm này còn không",
            reply="còn ạ",
            intent="product_inquiry",
            sentiment="neutral",
            created_at=datetime(2026, 1, 1, 10, 15),
        ),
    ]
    gift = GiftLog(
        id="gl1",
        session_id="sess-list-1",
        user_unique_id="u1",
        gift_name="Rose",
        diamond_count=1,
        repeat_count=5,
        total_diamonds=5,
        estimated_usd=0.025,
        created_at=datetime(2026, 1, 1, 10, 20),
    )
    db_session.add_all(msgs)
    db_session.add(gift)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()

    assert "session_list" in data
    assert len(data["session_list"]) == 1
    s = data["session_list"][0]
    assert s["id"] == "sess-list-1"
    assert s["comment_count"] == 3
    assert s["reply_count"] == 2
    assert s["reply_rate"] == 66.7
    assert s["gift_count"] == 1
    assert s["gift_diamonds"] == 5
    assert s["top_intent"] == "product_inquiry"
    assert s["duration_minutes"] == 90.0


async def test_overview_new_fields_default_empty(auth_client: AsyncClient, test_seller):
    """New fields return empty lists when no data."""
    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["sentiment_trend"] == []
    assert data["top_keywords_overall"] == []
    assert data["session_list"] == []
