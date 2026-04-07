"""Integration tests for Analytics API."""

import pytest
from httpx import AsyncClient


async def test_analytics_returns_zeros_for_new_seller(auth_client: AsyncClient, test_seller):
    """GET /api/v1/analytics/ returns zero stats for authenticated seller with no data."""
    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 0
    assert data["total_comments"] == 0
    assert data["total_replies"] == 0
    assert data["reply_rate"] == 0.0
    assert data["intent_breakdown"] == {}
    assert data["unanswered_count"] == 0


async def test_unauthenticated_returns_401(client: AsyncClient):
    """Unauthenticated requests return 401."""
    resp = await client.get("/api/v1/analytics/")
    assert resp.status_code == 401
