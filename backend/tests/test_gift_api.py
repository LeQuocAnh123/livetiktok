"""Tests for gift-related API endpoints."""

import pytest
from app.models.session import LiveSession
from app.models.gift import GiftLog


@pytest.mark.asyncio
async def test_get_session_gifts(auth_client, db_session, test_seller):
    """GET /api/v1/sessions/{id}/gifts returns gift logs for a session."""
    session = LiveSession(seller_id=test_seller.id, status="ended")
    db_session.add(session)
    await db_session.commit()

    gift1 = GiftLog(
        session_id=session.id,
        user_unique_id="viewer1",
        gift_name="Rose",
        diamond_count=1,
        repeat_count=5,
        total_diamonds=5,
        estimated_usd=0.025,
        thank_reply="Cam on ban!",
    )
    gift2 = GiftLog(
        session_id=session.id,
        user_unique_id="viewer2",
        gift_name="Lion",
        diamond_count=500,
        repeat_count=1,
        total_diamonds=500,
        estimated_usd=2.5,
    )
    db_session.add_all([gift1, gift2])
    await db_session.commit()

    resp = await auth_client.get(f"/api/v1/sessions/{session.id}/gifts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["gift_name"] in ("Rose", "Lion")


@pytest.mark.asyncio
async def test_get_session_gifts_empty(auth_client, db_session, test_seller):
    """GET /api/v1/sessions/{id}/gifts returns empty list when no gifts."""
    session = LiveSession(seller_id=test_seller.id, status="ended")
    db_session.add(session)
    await db_session.commit()

    resp = await auth_client.get(f"/api/v1/sessions/{session.id}/gifts")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_session_gifts_not_found(auth_client):
    """GET /api/v1/sessions/{id}/gifts returns 404 for unknown session."""
    resp = await auth_client.get("/api/v1/sessions/nonexistent/gifts")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_session_gifts_forbidden(auth_client, db_session):
    """GET /api/v1/sessions/{id}/gifts returns 403 for another seller's session."""
    from app.models.seller import Seller
    from app.core.security import hash_password
    from app.core.crypto import encrypt

    other_seller = Seller(
        id="other-seller-999",
        name="Other Shop",
        username="othershop",
        password_hash=hash_password("pass"),
        tiktok_unique_id="@other",
        tiktok_session_id_encrypted=encrypt("s"),
        tiktok_target_idc_encrypted=encrypt("t"),
    )
    db_session.add(other_seller)
    await db_session.commit()

    session = LiveSession(seller_id="other-seller-999", status="ended")
    db_session.add(session)
    await db_session.commit()

    resp = await auth_client.get(f"/api/v1/sessions/{session.id}/gifts")
    assert resp.status_code == 403
