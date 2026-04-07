async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_get_status_no_session(auth_client):
    response = await auth_client.get("/api/v1/sessions/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
    assert data["session"] is None


import pytest


@pytest.mark.asyncio
async def test_session_messages_404_for_unknown_session(auth_client):
    resp = await auth_client.get("/api/v1/sessions/nonexistent-id/messages")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_session_messages_empty_for_new_session(auth_client, db_session, seller_id: str):
    from app.models.session import LiveSession, SessionStatus
    import uuid

    session = LiveSession(
        id=str(uuid.uuid4()),
        seller_id=seller_id,
        status=SessionStatus.ENDED,
    )
    db_session.add(session)
    await db_session.commit()

    resp = await auth_client.get(f"/api/v1/sessions/{session.id}/messages")
    assert resp.status_code == 200
    assert resp.json() == []
