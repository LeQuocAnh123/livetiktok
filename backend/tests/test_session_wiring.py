"""Integration tests for session start/stop/history wiring."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SELLER_ID = "wiring-seller-001"


@pytest.fixture
async def seller(db_session):
    from app.models.seller import Seller
    from app.core.crypto import encrypt

    s = Seller(
        name="Wiring Shop",
        tiktok_unique_id="@wiringshop",
        tiktok_session_id_encrypted=encrypt("sess-abc"),
        tiktok_target_idc_encrypted=encrypt("useast1a"),
    )
    s.id = SELLER_ID
    db_session.add(s)
    await db_session.commit()
    return s


async def test_start_session_creates_live_session(client, seller):
    """POST /api/v1/sessions/start creates LiveSession with ACTIVE status."""
    with (
        patch("app.api.v1.sessions.TikTokLiveClient") as mock_tiktok_cls,
        patch("app.api.v1.sessions.LiveListener") as mock_listener_cls,
        patch("app.api.v1.sessions.get_embed_provider") as mock_embed_factory,
        patch("app.api.v1.sessions.get_reply_provider") as mock_reply_factory,
        patch("app.api.v1.sessions.asyncio.create_task"),
    ):
        mock_client = MagicMock()
        mock_client.web = MagicMock()
        mock_tiktok_cls.return_value = mock_client
        mock_listener = MagicMock()
        mock_listener.on_comment = MagicMock()
        mock_listener.on_disconnect = MagicMock()
        mock_listener_cls.return_value = mock_listener
        mock_embed_factory.return_value = AsyncMock()
        mock_reply_factory.return_value = AsyncMock()

        resp = await client.post("/api/v1/sessions/start", json={
            "seller_id": SELLER_ID,
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["session"]["status"] == "active"


async def test_start_session_twice_returns_400(client, seller):
    """Cannot start a second session while one is already active."""
    with (
        patch("app.api.v1.sessions.TikTokLiveClient") as mock_tiktok_cls,
        patch("app.api.v1.sessions.LiveListener") as mock_listener_cls,
        patch("app.api.v1.sessions.get_embed_provider"),
        patch("app.api.v1.sessions.get_reply_provider"),
        patch("app.api.v1.sessions.asyncio.create_task"),
    ):
        mock_client = MagicMock()
        mock_client.web = MagicMock()
        mock_tiktok_cls.return_value = mock_client
        mock_listener = MagicMock()
        mock_listener_cls.return_value = mock_listener

        await client.post("/api/v1/sessions/start", json={"seller_id": SELLER_ID})
        resp2 = await client.post("/api/v1/sessions/start", json={"seller_id": SELLER_ID})

    assert resp2.status_code == 400


async def test_stop_session(client, seller):
    """POST /api/v1/sessions/stop ends active session."""
    with (
        patch("app.api.v1.sessions.TikTokLiveClient") as mock_tiktok_cls,
        patch("app.api.v1.sessions.LiveListener") as mock_listener_cls,
        patch("app.api.v1.sessions.get_embed_provider"),
        patch("app.api.v1.sessions.get_reply_provider"),
        patch("app.api.v1.sessions.asyncio.create_task"),
    ):
        mock_client = MagicMock()
        mock_client.web = MagicMock()
        mock_tiktok_cls.return_value = mock_client
        mock_listener = MagicMock()
        mock_listener.stop = AsyncMock()
        mock_listener_cls.return_value = mock_listener

        await client.post("/api/v1/sessions/start", json={"seller_id": SELLER_ID})

    resp = await client.post("/api/v1/sessions/stop")
    assert resp.status_code == 200


async def test_stop_when_no_active_session_returns_400(client):
    """POST /stop with no active session returns 400."""
    resp = await client.post("/api/v1/sessions/stop")
    assert resp.status_code == 400


async def test_history_returns_list(client, seller):
    """GET /api/v1/sessions/history returns list of past sessions."""
    resp = await client.get("/api/v1/sessions/history?page=1&limit=20")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
