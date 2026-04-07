"""Tests for auth API endpoints."""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.models.seller import Seller


@pytest.fixture
async def test_seller(db_session):
    """Create a test seller with known credentials."""
    seller = Seller(
        id="test-seller-001",
        name="Test Shop",
        username="testshop",
        password_hash=hash_password("testpass123"),
        is_active=True,
        tiktok_unique_id="@testshop",
        tiktok_session_id_encrypted="enc_session",
        tiktok_target_idc_encrypted="enc_idc",
    )
    db_session.add(seller)
    await db_session.commit()
    return seller


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_seller):
    """Successful login returns seller info and sets cookie."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testshop", "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-seller-001"
    assert data["username"] == "testshop"
    assert data["name"] == "Test Shop"
    assert "access_token" in response.cookies


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, test_seller):
    """Invalid password returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testshop", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    """Unknown username returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "unknown", "password": "any"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_seller(client: AsyncClient, db_session):
    """Inactive seller cannot login."""
    seller = Seller(
        id="inactive-seller",
        name="Inactive Shop",
        username="inactive",
        password_hash=hash_password("pass123"),
        is_active=False,
        tiktok_unique_id="@inactive",
        tiktok_session_id_encrypted="enc",
        tiktok_target_idc_encrypted="enc",
    )
    db_session.add(seller)
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "inactive", "password": "pass123"},
    )
    assert response.status_code == 401
    assert "disabled" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_me_returns_seller_info(client: AsyncClient, test_seller):
    """GET /me returns current seller info when authenticated."""
    # First login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testshop", "password": "testpass123"},
    )
    # Copy cookie to client
    client.cookies.set("access_token", login_response.cookies.get("access_token"))

    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-seller-001"
    assert data["username"] == "testshop"
