"""Integration tests for sessions API."""

import pytest
import uuid

from app.models.session import LiveSession, SessionStatus


async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_get_status_no_session(auth_client, test_seller):
    response = await auth_client.get("/api/v1/sessions/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
    assert data["session"] is None


async def test_session_messages_404_for_unknown_session(auth_client, test_seller):
    resp = await auth_client.get("/api/v1/sessions/nonexistent-id/messages")
    assert resp.status_code == 404


async def test_session_messages_empty_for_new_session(auth_client, test_seller, db_session):
    session = LiveSession(
        id=str(uuid.uuid4()),
        seller_id=test_seller.id,
        status=SessionStatus.ENDED,
    )
    db_session.add(session)
    await db_session.commit()

    resp = await auth_client.get(f"/api/v1/sessions/{session.id}/messages")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_session_messages_forbidden_for_other_seller(auth_client, test_seller, db_session):
    """Cannot view messages for sessions owned by another seller."""
    session = LiveSession(
        id=str(uuid.uuid4()),
        seller_id="other-seller-id",
        status=SessionStatus.ENDED,
    )
    db_session.add(session)
    await db_session.commit()

    resp = await auth_client.get(f"/api/v1/sessions/{session.id}/messages")
    assert resp.status_code == 403


async def test_unauthenticated_returns_401(client):
    """Unauthenticated requests return 401."""
    resp = await client.get("/api/v1/sessions/status")
    assert resp.status_code == 401
