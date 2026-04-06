import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_returns_zeros_for_new_seller(client: AsyncClient, seller_id: str):
    resp = await client.get("/api/v1/analytics/", params={"seller_id": seller_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 0
    assert data["total_comments"] == 0
    assert data["total_replies"] == 0
    assert data["reply_rate"] == 0.0
    assert data["intent_breakdown"] == {}
    assert data["unanswered_count"] == 0


@pytest.mark.asyncio
async def test_analytics_404_for_unknown_seller(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/", params={"seller_id": "nonexistent"})
    assert resp.status_code == 404
