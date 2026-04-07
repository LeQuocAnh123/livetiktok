"""Tests for gift analytics in GET /api/v1/analytics/."""

import pytest
from app.models.session import LiveSession
from app.models.gift import GiftLog


@pytest.mark.asyncio
async def test_analytics_includes_gift_stats(auth_client, db_session, test_seller):
    """Analytics response includes gift_stats with correct aggregations."""
    session = LiveSession(seller_id=test_seller.id, status="ended")
    db_session.add(session)
    await db_session.commit()

    gifts = [
        GiftLog(
            session_id=session.id,
            user_unique_id="viewer1",
            gift_name="Rose",
            diamond_count=1,
            repeat_count=10,
            total_diamonds=10,
            estimated_usd=0.05,
        ),
        GiftLog(
            session_id=session.id,
            user_unique_id="viewer1",
            gift_name="Lion",
            diamond_count=500,
            repeat_count=1,
            total_diamonds=500,
            estimated_usd=2.5,
        ),
        GiftLog(
            session_id=session.id,
            user_unique_id="viewer2",
            gift_name="Rose",
            diamond_count=1,
            repeat_count=5,
            total_diamonds=5,
            estimated_usd=0.025,
        ),
    ]
    db_session.add_all(gifts)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()

    gs = data["gift_stats"]
    assert gs["total_gifts"] == 3
    assert gs["total_diamonds"] == 515
    assert gs["estimated_usd"] == pytest.approx(2.575)

    # Top gifters: viewer1 has 510, viewer2 has 5
    assert len(gs["top_gifters"]) == 2
    assert gs["top_gifters"][0]["user"] == "viewer1"
    assert gs["top_gifters"][0]["total_diamonds"] == 510
    assert gs["top_gifters"][0]["gift_count"] == 2

    # Gift breakdown: Rose=15 diamonds (2 gifts), Lion=500 diamonds (1 gift)
    breakdown = {g["gift_name"]: g for g in gs["gift_breakdown"]}
    assert breakdown["Rose"]["count"] == 2
    assert breakdown["Rose"]["total_diamonds"] == 15
    assert breakdown["Lion"]["count"] == 1
    assert breakdown["Lion"]["total_diamonds"] == 500


@pytest.mark.asyncio
async def test_analytics_gift_stats_empty(auth_client, db_session, test_seller):
    """Analytics returns zeroed gift_stats when no gifts exist."""
    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()

    gs = data["gift_stats"]
    assert gs["total_gifts"] == 0
    assert gs["total_diamonds"] == 0
    assert gs["estimated_usd"] == 0.0
    assert gs["top_gifters"] == []
    assert gs["gift_breakdown"] == []
