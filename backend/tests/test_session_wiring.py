"""Integration tests for session start/stop/history wiring."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def test_start_session_creates_live_session(auth_client, test_seller):
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

        # No body needed - seller_id comes from JWT
        resp = await auth_client.post("/api/v1/sessions/start")

    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["session"]["status"] == "active"
    assert data["session"]["seller_id"] == test_seller.id


async def test_start_session_twice_returns_400(auth_client, test_seller):
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

        await auth_client.post("/api/v1/sessions/start")
        resp2 = await auth_client.post("/api/v1/sessions/start")

    assert resp2.status_code == 400


async def test_stop_session(auth_client, test_seller):
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

        await auth_client.post("/api/v1/sessions/start")

    resp = await auth_client.post("/api/v1/sessions/stop")
    assert resp.status_code == 200


async def test_stop_when_no_active_session_returns_400(auth_client, test_seller):
    """POST /stop with no active session returns 400."""
    resp = await auth_client.post("/api/v1/sessions/stop")
    assert resp.status_code == 400


async def test_history_returns_list(auth_client, test_seller):
    """GET /api/v1/sessions/history returns list of past sessions (only for authenticated seller)."""
    resp = await auth_client.get("/api/v1/sessions/history?page=1&limit=20")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
