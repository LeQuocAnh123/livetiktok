"""Tests for ChromaDB retriever — uses in-memory EphemeralClient."""
import chromadb
import pytest

SELLER_ID = "test-seller-123"


@pytest.fixture
def chroma_client(monkeypatch):
    """Override retriever's lazy client with an in-memory EphemeralClient."""
    import app.core.rag.retriever as retriever_mod
    client = chromadb.EphemeralClient()
    monkeypatch.setattr(retriever_mod, "_chroma_client", client)
    return client


async def test_add_and_query_chunk(chroma_client):
    """add_chunk() stores embedding, query() retrieves it."""
    from app.core.rag.retriever import add_chunk, query

    embedding = [0.1] * 1536  # text-embedding-3-small dimension

    await add_chunk(
        seller_id=SELLER_ID,
        chunk_id="chunk-001",
        content="Áo cotton màu trắng giá 150k",
        embedding=embedding,
        metadata={"category": "product"},
    )

    results = await query(SELLER_ID, embedding, n_results=1)

    assert len(results) == 1
    assert results[0]["id"] == "chunk-001"
    assert results[0]["content"] == "Áo cotton màu trắng giá 150k"
    assert results[0]["metadata"]["category"] == "product"


async def test_delete_chunk(chroma_client):
    """delete_chunk() removes chunk from collection."""
    from app.core.rag.retriever import add_chunk, delete_chunk, query

    embedding = [0.2] * 1536
    await add_chunk(SELLER_ID, "chunk-002", "To be deleted", embedding, {})

    results = await query(SELLER_ID, embedding, n_results=1)
    assert len(results) == 1

    await delete_chunk(SELLER_ID, "chunk-002")

    results_after = await query(SELLER_ID, embedding, n_results=3)
    ids = [r["id"] for r in results_after]
    assert "chunk-002" not in ids


async def test_query_returns_empty_when_no_chunks(chroma_client):
    """query() returns empty list when collection has no documents."""
    from app.core.rag.retriever import query

    embedding = [0.3] * 1536
    results = await query("empty-seller", embedding, n_results=3)
    assert results == []


async def test_add_chunk_upserts_existing(chroma_client):
    """add_chunk() with same id updates the existing entry."""
    from app.core.rag.retriever import add_chunk, query

    emb1 = [0.1] * 1536
    emb2 = [0.9] * 1536

    await add_chunk(SELLER_ID, "chunk-upsert", "Original content", emb1, {})
    await add_chunk(SELLER_ID, "chunk-upsert", "Updated content", emb2, {})

    results = await query(SELLER_ID, emb2, n_results=1)
    assert results[0]["id"] == "chunk-upsert"
    assert results[0]["content"] == "Updated content"
