"""Integration tests for Settings API."""

from unittest.mock import AsyncMock, patch

import pytest

SELLER_ID = "settings-seller-001"


@pytest.fixture
async def seller(db_session):
    from app.models.seller import Seller
    from app.core.crypto import encrypt

    s = Seller(
        name="Test Shop",
        tiktok_unique_id="@testshop",
        tiktok_session_id_encrypted=encrypt("sess123"),
        tiktok_target_idc_encrypted=encrypt("useast1a"),
    )
    s.id = SELLER_ID
    db_session.add(s)
    await db_session.commit()
    return s


async def test_get_settings(auth_client, seller):
    """GET /api/v1/settings/?seller_id=... returns current bot settings."""
    resp = await auth_client.get(f"/api/v1/settings/?seller_id={SELLER_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tone"] == "friendly"
    assert "blacklist_keywords" in data
    assert "auto_reply_enabled" in data


async def test_update_settings(auth_client, seller):
    """PUT /api/v1/settings/ updates bot_settings JSON."""
    resp = await auth_client.put(
        f"/api/v1/settings/?seller_id={SELLER_ID}",
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


async def test_update_settings_merges_not_replaces(auth_client, seller):
    """PUT only updates provided fields, preserves others."""
    # Set initial
    await auth_client.put(
        f"/api/v1/settings/?seller_id={SELLER_ID}",
        json={
            "tone": "friendly",
            "reply_delay_min": 5,
        },
    )
    # Update only tone
    resp = await auth_client.put(
        f"/api/v1/settings/?seller_id={SELLER_ID}",
        json={
            "tone": "casual",
        },
    )
    data = resp.json()
    assert data["tone"] == "casual"
    assert data["reply_delay_min"] == 5  # preserved


async def test_test_reply(auth_client, seller):
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
        mock_reply_provider.generate_reply = AsyncMock(return_value="Dạ giá 150k ạ!")
        mock_reply_factory.return_value = mock_reply_provider

        resp = await auth_client.post(
            "/api/v1/settings/test-reply",
            json={
                "seller_id": SELLER_ID,
                "comment": "Giá bao nhiêu?",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"] == "Dạ giá 150k ạ!"
    assert "intent" in data
    assert "chunks_used" in data


async def test_get_settings_not_found(auth_client):
    """GET settings for unknown seller returns 404."""
    resp = await auth_client.get("/api/v1/settings/?seller_id=unknown")
    assert resp.status_code == 404
