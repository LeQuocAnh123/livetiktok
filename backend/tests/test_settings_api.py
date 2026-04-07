"""Integration tests for Settings API."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.ai.base import LLMResult


async def test_get_settings(auth_client, test_seller):
    """GET /api/v1/settings/ returns current bot settings for authenticated seller."""
    resp = await auth_client.get("/api/v1/settings/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tone"] == "friendly"
    assert "blacklist_keywords" in data
    assert "auto_reply_enabled" in data


async def test_update_settings(auth_client, test_seller):
    """PUT /api/v1/settings/ updates bot_settings JSON for authenticated seller."""
    resp = await auth_client.put(
        "/api/v1/settings/",
        json={
            "tone": "professional",
            "user_cooldown_seconds": 30,
            "auto_reply_enabled": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tone"] == "professional"
    assert data["user_cooldown_seconds"] == 30
    assert data["auto_reply_enabled"] is False


async def test_update_settings_merges_not_replaces(auth_client, test_seller):
    """PUT only updates provided fields, preserves others."""
    # Set initial
    await auth_client.put(
        "/api/v1/settings/",
        json={
            "tone": "friendly",
            "reply_delay_min": 5,
        },
    )
    # Update only tone
    resp = await auth_client.put(
        "/api/v1/settings/",
        json={
            "tone": "casual",
        },
    )
    data = resp.json()
    assert data["tone"] == "casual"
    assert data["reply_delay_min"] == 5  # preserved


async def test_test_reply(auth_client, test_seller):
    """POST /api/v1/settings/test-reply returns a preview reply without sending to TikTok."""
    with (
        patch("app.api.v1.settings.get_embed_provider") as mock_embed_factory,
        patch("app.api.v1.settings.retriever.query", new_callable=AsyncMock) as mock_query,
        patch("app.api.v1.settings.get_reply_provider") as mock_reply_factory,
    ):
        mock_embed_provider = AsyncMock()
        mock_embed_provider.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_factory.return_value = mock_embed_provider

        mock_query.return_value = [
            {"id": "c1", "content": "Áo giá 150k", "metadata": {}, "distance": 0.1}
        ]

        mock_reply_provider = AsyncMock()
        mock_reply_provider.generate_reply = AsyncMock(
            return_value=LLMResult(
                intent="product_inquiry", sentiment="neutral", reply="Dạ giá 150k ạ!"
            )
        )
        mock_reply_factory.return_value = mock_reply_provider

        resp = await auth_client.post(
            "/api/v1/settings/test-reply",
            json={
                "comment": "Giá bao nhiêu?",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"] == "Dạ giá 150k ạ!"
    assert "intent" in data
    assert "chunks_used" in data


async def test_unauthenticated_returns_401(client):
    """Unauthenticated requests return 401."""
    resp = await client.get("/api/v1/settings/")
    assert resp.status_code == 401
