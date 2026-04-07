"""Integration tests for session detail analytics endpoint."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.gift import GiftLog
from app.models.message import MessageLog
from app.models.session import LiveSession


async def test_session_detail_returns_full_analytics(
    auth_client: AsyncClient, db_session, test_seller
):
    """GET /api/v1/analytics/sessions/{id} returns complete analytics."""
    session = LiveSession(
        id="sess-detail-1",
        seller_id=test_seller.id,
        started_at=datetime(2026, 1, 1, 10, 0),
        ended_at=datetime(2026, 1, 1, 10, 30),
    )
    db_session.add(session)

    msgs = [
        MessageLog(
            id="sd1",
            session_id="sess-detail-1",
            user_unique_id="u1",
            comment="giá bao nhiêu",
            reply="100k ạ",
            intent="product_inquiry",
            sentiment="neutral",
            created_at=datetime(2026, 1, 1, 10, 2),
        ),
        MessageLog(
            id="sd2",
            session_id="sess-detail-1",
            user_unique_id="u2",
            comment="chào shop",
            reply="chào bạn",
            intent="greeting",
            sentiment="positive",
            created_at=datetime(2026, 1, 1, 10, 7),
        ),
        MessageLog(
            id="sd3",
            session_id="sess-detail-1",
            user_unique_id="u3",
            comment="giá sản phẩm này",
            reply=None,
            intent="product_inquiry",
            sentiment="neutral",
            created_at=datetime(2026, 1, 1, 10, 12),
        ),
    ]
    gift = GiftLog(
        id="sg1",
        session_id="sess-detail-1",
        user_unique_id="u1",
        gift_name="Rose",
        diamond_count=1,
        repeat_count=10,
        total_diamonds=10,
        estimated_usd=0.05,
        created_at=datetime(2026, 1, 1, 10, 5),
    )
    db_session.add_all(msgs)
    db_session.add(gift)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/sessions/sess-detail-1")
    assert resp.status_code == 200
    data = resp.json()

    # session_info
    assert data["session_info"]["id"] == "sess-detail-1"
    assert data["session_info"]["duration_minutes"] == 30.0

    # summary
    assert data["summary"]["total_comments"] == 3
    assert data["summary"]["total_replies"] == 2
    assert data["summary"]["reply_rate"] == 66.7
    assert data["summary"]["total_gifts"] == 1
    assert data["summary"]["total_diamonds"] == 10
    assert data["summary"]["estimated_usd"] == 0.05

    # timeline (30 min / 5 min = 6 buckets)
    assert len(data["timeline"]) == 6

    # keywords
    assert len(data["top_keywords"]) > 0
    words = [kw["word"] for kw in data["top_keywords"]]
    assert "giá" in words

    # breakdowns
    assert data["intent_breakdown"]["product_inquiry"] == 2
    assert data["intent_breakdown"]["greeting"] == 1
    assert data["sentiment_breakdown"]["neutral"] == 2
    assert data["sentiment_breakdown"]["positive"] == 1

    # engagement
    assert data["engagement_metrics"]["product_inquiry_rate"] == pytest.approx(66.7, abs=0.1)
    assert data["engagement_metrics"]["unique_commenters"] == 3


async def test_session_detail_404_for_nonexistent(auth_client: AsyncClient, test_seller):
    """Returns 404 for a session that doesn't exist."""
    resp = await auth_client.get("/api/v1/analytics/sessions/nonexistent-id")
    assert resp.status_code == 404


async def test_session_detail_403_for_other_seller(
    auth_client: AsyncClient, db_session, test_seller
):
    """Returns 403 for a session belonging to another seller."""
    session = LiveSession(
        id="sess-other-1",
        seller_id="other-seller-id",
        started_at=datetime(2026, 1, 1, 10, 0),
    )
    db_session.add(session)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/sessions/sess-other-1")
    assert resp.status_code == 403


async def test_session_detail_empty_session(auth_client: AsyncClient, db_session, test_seller):
    """Returns empty timeline and zero stats for session with no messages."""
    session = LiveSession(
        id="sess-empty-1",
        seller_id=test_seller.id,
        started_at=datetime(2026, 1, 1, 10, 0),
        ended_at=datetime(2026, 1, 1, 10, 10),
    )
    db_session.add(session)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/sessions/sess-empty-1")
    assert resp.status_code == 200
    data = resp.json()

    assert data["summary"]["total_comments"] == 0
    assert data["summary"]["total_replies"] == 0
    assert data["summary"]["reply_rate"] == 0.0
    assert data["summary"]["total_gifts"] == 0
    assert len(data["timeline"]) == 2  # 10 min / 5 min = 2 buckets
    assert data["top_keywords"] == []
    assert data["engagement_metrics"]["unique_commenters"] == 0
    assert data["engagement_metrics"]["peak_minute"] is None
