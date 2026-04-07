"""Integration tests for knowledge base CRUD API."""

from unittest.mock import AsyncMock, patch

import pytest


async def test_create_knowledge_chunk(auth_client, test_seller):
    """POST /api/v1/knowledge/ creates chunk and triggers embed."""
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        resp = await auth_client.post(
            "/api/v1/knowledge/",
            json={
                "content": "Áo cotton giá 150k",
                "category": "product",
                "metadata": {"product_name": "Áo Cotton"},
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Áo cotton giá 150k"
    assert data["seller_id"] == test_seller.id
    assert "id" in data


async def test_list_knowledge_chunks(auth_client, test_seller):
    """GET /api/v1/knowledge/ returns paginated chunks for authenticated seller."""
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        await auth_client.post(
            "/api/v1/knowledge/",
            json={
                "content": "Sản phẩm A",
                "category": "faq",
                "metadata": {},
            },
        )

    resp = await auth_client.get("/api/v1/knowledge/?page=1&limit=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


async def test_update_knowledge_chunk(auth_client, test_seller):
    """PUT /api/v1/knowledge/{id} updates content and sets needs_reembed=True."""
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        create_resp = await auth_client.post(
            "/api/v1/knowledge/",
            json={
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


async def test_delete_knowledge_chunk(auth_client, test_seller):
    """DELETE /api/v1/knowledge/{id} removes chunk from DB and ChromaDB."""
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        create_resp = await auth_client.post(
            "/api/v1/knowledge/",
            json={
                "content": "To delete",
                "category": "faq",
                "metadata": {},
            },
        )
    chunk_id = create_resp.json()["id"]

    with patch("app.core.rag.retriever.delete_chunk", new_callable=AsyncMock):
        resp = await auth_client.delete(f"/api/v1/knowledge/{chunk_id}")

    assert resp.status_code == 204


async def test_delete_not_found(auth_client, test_seller):
    """DELETE on non-existent chunk returns 404."""
    with patch("app.core.rag.retriever.delete_chunk", new_callable=AsyncMock):
        resp = await auth_client.delete("/api/v1/knowledge/non-existent-id")
    assert resp.status_code == 404


async def test_update_other_seller_chunk_forbidden(auth_client, test_seller, db_session):
    """PUT /api/v1/knowledge/{id} returns 403 for chunk owned by another seller."""
    from app.models.knowledge import KnowledgeChunk, KnowledgeCategory

    # Create a chunk owned by a different seller
    other_chunk = KnowledgeChunk(
        seller_id="other-seller-id",
        content="Other seller's content",
        category=KnowledgeCategory.FAQ,
        metadata_={},
        needs_reembed=False,
    )
    db_session.add(other_chunk)
    await db_session.commit()
    await db_session.refresh(other_chunk)

    resp = await auth_client.put(
        f"/api/v1/knowledge/{other_chunk.id}",
        json={"content": "Trying to update"},
    )
    assert resp.status_code == 403
    assert "Not authorized" in resp.json()["detail"]


async def test_delete_other_seller_chunk_forbidden(auth_client, test_seller, db_session):
    """DELETE /api/v1/knowledge/{id} returns 403 for chunk owned by another seller."""
    from app.models.knowledge import KnowledgeChunk, KnowledgeCategory

    # Create a chunk owned by a different seller
    other_chunk = KnowledgeChunk(
        seller_id="other-seller-id",
        content="Other seller's content",
        category=KnowledgeCategory.FAQ,
        metadata_={},
        needs_reembed=False,
    )
    db_session.add(other_chunk)
    await db_session.commit()
    await db_session.refresh(other_chunk)

    with patch("app.core.rag.retriever.delete_chunk", new_callable=AsyncMock):
        resp = await auth_client.delete(f"/api/v1/knowledge/{other_chunk.id}")

    assert resp.status_code == 403
    assert "Not authorized" in resp.json()["detail"]


async def test_list_only_returns_own_chunks(auth_client, test_seller, db_session):
    """GET /api/v1/knowledge/ only returns chunks owned by authenticated seller."""
    from app.models.knowledge import KnowledgeChunk, KnowledgeCategory

    # Create a chunk for the test seller
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        await auth_client.post(
            "/api/v1/knowledge/",
            json={
                "content": "My content",
                "category": "faq",
                "metadata": {},
            },
        )

    # Create a chunk owned by a different seller directly in DB
    other_chunk = KnowledgeChunk(
        seller_id="other-seller-id",
        content="Other seller's content",
        category=KnowledgeCategory.FAQ,
        metadata_={},
        needs_reembed=False,
    )
    db_session.add(other_chunk)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/knowledge/?page=1&limit=100")
    assert resp.status_code == 200
    data = resp.json()

    # All returned chunks should belong to test_seller
    for item in data["items"]:
        assert item["seller_id"] == test_seller.id

    # Other seller's chunk should not be in the list
    chunk_ids = [item["id"] for item in data["items"]]
    assert other_chunk.id not in chunk_ids


async def test_unauthenticated_returns_401(client):
    """Unauthenticated requests return 401."""
    resp = await client.get("/api/v1/knowledge/?page=1&limit=20")
    assert resp.status_code == 401
