"""Integration tests for knowledge base CRUD API."""

from unittest.mock import AsyncMock, patch

import pytest

SELLER_ID = "seller-test-001"


@pytest.fixture
async def seller(db_session):
    """Create a test seller in the DB."""
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


async def test_create_knowledge_chunk(auth_client, seller):
    """POST /api/v1/knowledge/ creates chunk and triggers embed."""
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        resp = await auth_client.post(
            "/api/v1/knowledge/",
            json={
                "seller_id": SELLER_ID,
                "content": "Áo cotton giá 150k",
                "category": "product",
                "metadata": {"product_name": "Áo Cotton"},
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Áo cotton giá 150k"
    assert data["seller_id"] == SELLER_ID
    assert "id" in data


async def test_list_knowledge_chunks(auth_client, seller):
    """GET /api/v1/knowledge/?seller_id=... returns paginated chunks."""
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        await auth_client.post(
            "/api/v1/knowledge/",
            json={
                "seller_id": SELLER_ID,
                "content": "Sản phẩm A",
                "category": "faq",
                "metadata": {},
            },
        )

    resp = await auth_client.get(f"/api/v1/knowledge/?seller_id={SELLER_ID}&page=1&limit=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


async def test_update_knowledge_chunk(auth_client, seller):
    """PUT /api/v1/knowledge/{id} updates content and sets needs_reembed=True."""
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        create_resp = await auth_client.post(
            "/api/v1/knowledge/",
            json={
                "seller_id": SELLER_ID,
                "content": "Original content",
                "category": "faq",
                "metadata": {},
            },
        )
    chunk_id = create_resp.json()["id"]

    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock) as mock_embed:
        resp = await auth_client.put(
            f"/api/v1/knowledge/{chunk_id}",
            json={
                "content": "Updated content",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["content"] == "Updated content"
    mock_embed.assert_called_once()


async def test_delete_knowledge_chunk(auth_client, seller):
    """DELETE /api/v1/knowledge/{id} removes chunk from DB and ChromaDB."""
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        create_resp = await auth_client.post(
            "/api/v1/knowledge/",
            json={
                "seller_id": SELLER_ID,
                "content": "To delete",
                "category": "faq",
                "metadata": {},
            },
        )
    chunk_id = create_resp.json()["id"]

    with patch("app.core.rag.retriever.delete_chunk", new_callable=AsyncMock):
        resp = await auth_client.delete(f"/api/v1/knowledge/{chunk_id}")

    assert resp.status_code == 204


async def test_list_returns_empty_for_unknown_seller(auth_client):
    """GET /api/v1/knowledge/ returns empty list for unknown seller."""
    resp = await auth_client.get("/api/v1/knowledge/?seller_id=unknown-seller&page=1&limit=20")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_delete_not_found(auth_client, seller):
    """DELETE on non-existent chunk returns 404."""
    with patch("app.core.rag.retriever.delete_chunk", new_callable=AsyncMock):
        resp = await auth_client.delete("/api/v1/knowledge/non-existent-id")
    assert resp.status_code == 404
