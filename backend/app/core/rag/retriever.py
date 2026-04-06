"""ChromaDB retriever — one collection per seller, lazy client init."""
import logging
from typing import Any

import chromadb

from app.config import get_settings

logger = logging.getLogger(__name__)

# Lazy singleton — never initialized at import time
_chroma_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        path = get_settings().chroma_path
        _chroma_client = chromadb.PersistentClient(path=path)
        logger.info("ChromaDB client initialized at %s", path)
    return _chroma_client


def _collection_name(seller_id: str) -> str:
    return f"seller_{seller_id}"


def _get_collection(seller_id: str):
    return _get_client().get_or_create_collection(
        name=_collection_name(seller_id),
        metadata={"hnsw:space": "cosine"},
    )


async def add_chunk(
    seller_id: str,
    chunk_id: str,
    content: str,
    embedding: list[float],
    metadata: dict[str, Any],
) -> None:
    """Add or update a chunk in the seller's ChromaDB collection (upsert)."""
    collection = _get_collection(seller_id)
    # ChromaDB requires non-empty metadata dict or None
    meta = metadata if metadata else None
    collection.upsert(
        ids=[chunk_id],
        embeddings=[embedding],
        documents=[content],
        metadatas=[meta],
    )
    logger.debug("Upserted chunk %s into collection %s", chunk_id, _collection_name(seller_id))


async def delete_chunk(seller_id: str, chunk_id: str) -> None:
    """Remove a chunk from the seller's ChromaDB collection."""
    collection = _get_collection(seller_id)
    collection.delete(ids=[chunk_id])
    logger.debug("Deleted chunk %s from collection %s", chunk_id, _collection_name(seller_id))


async def query(
    seller_id: str,
    embedding: list[float],
    n_results: int = 3,
) -> list[dict[str, Any]]:
    """Query top-N most similar chunks. Returns empty list if collection is empty."""
    collection = _get_collection(seller_id)
    count = collection.count()
    if count == 0:
        return []

    actual_n = min(n_results, count)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=actual_n,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for chunk_id, doc, meta, dist in zip(ids, documents, metadatas, distances):
        chunks.append({
            "id": chunk_id,
            "content": doc,
            "metadata": meta or {},
            "distance": dist,
        })

    return chunks
