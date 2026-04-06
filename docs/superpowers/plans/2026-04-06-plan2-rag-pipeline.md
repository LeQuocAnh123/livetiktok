# RAG Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng RAG pipeline hoàn chỉnh: AI providers (Claude + OpenAI), ChromaDB retriever, comment filter, Knowledge Base API, Settings API — và wire toàn bộ vào sessions start/stop và WebSocket commands.

**Architecture:** RAG pipeline gồm 4 tầng độc lập: (1) AI abstraction layer (`core/ai/`) với Protocol pattern, (2) ChromaDB retriever (`core/rag/retriever.py`) dùng lazy client, (3) comment filter (`core/rag/filter.py`) cho blacklist/intent/cooldown, (4) orchestration pipeline (`core/rag/pipeline.py`). Sessions API wires listener → filter → RAG → replier → DB save → WS broadcast. Background tasks handle re-embed khi chunk được update.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x async, ChromaDB 0.5+, OpenAI SDK (embeddings + optional reply), Anthropic SDK (reply), openpyxl (Excel import), pytest-asyncio

**Spec:** `docs/superpowers/specs/2026-04-06-tiktok-live-ai-bot-design.md`

**Depends on:** Plan 1 backend core (all 9 tasks must be complete)

---

## File Map

```
backend/
├── pyproject.toml                        # MODIFY — add chromadb, openai, anthropic, openpyxl
├── app/
│   ├── database.py                       # MODIFY — add public get_session_factory()
│   ├── core/
│   │   ├── ai/
│   │   │   ├── __init__.py               # CREATE (empty)
│   │   │   ├── base.py                   # CREATE — AIProvider + EmbedProvider Protocol
│   │   │   ├── claude.py                 # CREATE — Anthropic AIProvider implementation
│   │   │   ├── openai_llm.py             # CREATE — OpenAI AIProvider implementation
│   │   │   ├── openai_embed.py           # CREATE — OpenAI EmbedProvider implementation
│   │   │   └── factory.py               # CREATE — get_reply_provider() + get_embed_provider()
│   │   └── rag/
│   │       ├── __init__.py               # CREATE (empty)
│   │       ├── retriever.py              # CREATE — ChromaDB client + CRUD ops
│   │       ├── filter.py                 # CREATE — blacklist, intent detection, cooldown
│   │       └── pipeline.py              # CREATE — orchestrate full RAG flow
│   ├── api/
│   │   ├── v1/
│   │   │   ├── knowledge.py              # CREATE — CRUD + bulk upload
│   │   │   ├── settings.py              # CREATE — get/put settings + test-reply
│   │   │   └── sessions.py              # MODIFY — add start/stop/history + wire RAG
│   │   └── ws.py                        # MODIFY — handle pause/resume/manual_reply
│   ├── schemas/
│   │   ├── knowledge.py                  # CREATE — KnowledgeChunk schemas
│   │   └── settings.py                  # CREATE — BotSettings schema
│   └── main.py                          # MODIFY — include knowledge + settings routers
└── tests/
    ├── conftest.py                       # MODIFY — add chroma_client fixture + state reset
    ├── test_ai_providers.py              # CREATE — unit tests for AI providers + factory
    ├── test_retriever.py                 # CREATE — unit tests for ChromaDB retriever
    ├── test_filter.py                    # CREATE — unit tests for comment filter
    ├── test_pipeline.py                  # CREATE — unit tests for RAG pipeline (full mock)
    ├── test_knowledge_api.py             # CREATE — integration tests for knowledge CRUD
    ├── test_settings_api.py              # CREATE — integration tests for settings API
    └── test_session_wiring.py           # CREATE — integration tests for start/stop/history
```

---

## Critical Implementation Notes

- **ChromaDB client:** always lazy-initialized via `_get_client()` — never at import time
- **AI providers:** never call real APIs in tests — always mock `anthropic.AsyncAnthropic` and `openai.AsyncOpenAI`
- **Background DB access:** use `get_session_factory()` (public, from `database.py`) inside background tasks, never `get_db()` dependency
- **`_active_*` state:** sessions.py gains `_active_listener`, `_active_replier`, `_active_pipeline`, `_bot_paused`, `_reply_count` module-level globals; conftest must reset ALL of them between tests
- **`send_room_chat` signature:** `await web_client.send_room_chat(content=content)` — no other args
- **TikTok event user field:** `event.user_info.unique_id` (NOT `event.user`)
- **ChromaDB collection name:** `seller_{seller_id}` (e.g., `seller_abc123`)
- **Fernet key:** `get_settings().secret_key` must be valid Fernet key (base64-urlsafe, 32 bytes) — set `SECRET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")` in `.env`

---

## Task 1: Add Dependencies + Public DB Accessor

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/database.py`

- [ ] **Step 1: Add new deps to pyproject.toml**

In `backend/pyproject.toml`, add to `dependencies`:

```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "aiosqlite>=0.19.0",
    "pydantic-settings>=2.0.0",
    "cryptography>=42.0.0",
    "httpx>=0.26.0",
    "python-dotenv>=1.0.0",
    "websockets>=12.0",
    "python-multipart>=0.0.9",
    # Plan 2 additions:
    "chromadb>=0.5.0",
    "openai>=1.0.0",
    "anthropic>=0.20.0",
    "openpyxl>=3.1.0",
]
```

- [ ] **Step 2: Install new dependencies**

Run from `backend/` directory:
```bash
pip install -e .
```

Expected: packages install without error. Verify with:
```bash
python -c "import chromadb, openai, anthropic, openpyxl; print('OK')"
```

- [ ] **Step 3: Add `get_session_factory` public export to database.py**

Open `backend/app/database.py`. After `_get_session_factory()`, add:

```python
def get_session_factory():
    """Public accessor for background tasks that need their own DB session."""
    return _get_session_factory()
```

Also update the `get_db` return type annotation:

```python
async def get_db():
    async with _get_session_factory()() as session:
        yield session
```

(no type annotation needed — simpler)

- [ ] **Step 4: Run existing tests to verify nothing broke**

```bash
cd backend && pytest tests/ -v --tb=short
```

Expected: all existing tests pass (12 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/app/database.py
git commit -m "chore: add RAG/AI deps + public get_session_factory"
```

---

## Task 2: AI Provider Protocols + Implementations + Factory

**Files:**
- Create: `backend/app/core/ai/__init__.py`
- Create: `backend/app/core/ai/base.py`
- Create: `backend/app/core/ai/claude.py`
- Create: `backend/app/core/ai/openai_llm.py`
- Create: `backend/app/core/ai/openai_embed.py`
- Create: `backend/app/core/ai/factory.py`
- Create: `backend/tests/test_ai_providers.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_ai_providers.py`:

```python
"""Tests for AI provider abstraction layer."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Protocol conformance tests (duck-typing — no real API calls)
# ---------------------------------------------------------------------------

async def test_claude_generate_reply_calls_anthropic():
    """ClaudeProvider.generate_reply() calls Anthropic messages.create."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Dạ còn hàng ạ!")]

    with patch("app.core.ai.claude.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        from app.core.ai.claude import ClaudeProvider
        provider = ClaudeProvider(api_key="test-key")
        result = await provider.generate_reply(
            system="You are a helpful assistant.",
            context="Sản phẩm còn 10 cái.",
            user_msg="Còn hàng không?",
        )

    assert result == "Dạ còn hàng ạ!"
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["system"] == "You are a helpful assistant."


async def test_openai_llm_generate_reply_calls_openai():
    """OpenAILLMProvider.generate_reply() calls OpenAI chat completions."""
    mock_choice = MagicMock()
    mock_choice.message.content = "Giá 200k ạ!"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("app.core.ai.openai_llm.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        from app.core.ai.openai_llm import OpenAILLMProvider
        provider = OpenAILLMProvider(api_key="test-key")
        result = await provider.generate_reply(
            system="You are a seller bot.",
            context="Áo giá 200k.",
            user_msg="Giá bao nhiêu?",
        )

    assert result == "Giá 200k ạ!"


async def test_openai_embed_returns_embedding():
    """OpenAIEmbedProvider.embed() returns a list of floats."""
    mock_data = MagicMock()
    mock_data.embedding = [0.1, 0.2, 0.3]
    mock_response = MagicMock()
    mock_response.data = [mock_data]

    with patch("app.core.ai.openai_embed.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        from app.core.ai.openai_embed import OpenAIEmbedProvider
        provider = OpenAIEmbedProvider(api_key="test-key")
        result = await provider.embed("test text")

    assert result == [0.1, 0.2, 0.3]
    call_kwargs = mock_client.embeddings.create.call_args.kwargs
    assert call_kwargs["model"] == "text-embedding-3-small"
    assert call_kwargs["input"] == "test text"


def test_factory_claude_provider(monkeypatch):
    """get_reply_provider() returns ClaudeProvider when ai_reply_provider='claude'."""
    monkeypatch.setenv("SECRET_KEY", "dGVzdC1rZXktMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM=")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("AI_REPLY_PROVIDER", "claude")

    # Clear lru_cache so env vars take effect
    from app.config import get_settings
    get_settings.cache_clear()

    from app.core.ai import factory
    from app.core.ai.claude import ClaudeProvider
    provider = factory.get_reply_provider()
    assert isinstance(provider, ClaudeProvider)

    get_settings.cache_clear()


def test_factory_openai_provider(monkeypatch):
    """get_reply_provider() returns OpenAILLMProvider when ai_reply_provider='openai'."""
    monkeypatch.setenv("SECRET_KEY", "dGVzdC1rZXktMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM=")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("AI_REPLY_PROVIDER", "openai")

    from app.config import get_settings
    get_settings.cache_clear()

    from app.core.ai import factory
    from app.core.ai.openai_llm import OpenAILLMProvider
    provider = factory.get_reply_provider()
    assert isinstance(provider, OpenAILLMProvider)

    get_settings.cache_clear()


def test_factory_embed_provider(monkeypatch):
    """get_embed_provider() returns OpenAIEmbedProvider."""
    monkeypatch.setenv("SECRET_KEY", "dGVzdC1rZXktMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM=")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    from app.config import get_settings
    get_settings.cache_clear()

    from app.core.ai import factory
    from app.core.ai.openai_embed import OpenAIEmbedProvider
    provider = factory.get_embed_provider()
    assert isinstance(provider, OpenAIEmbedProvider)

    get_settings.cache_clear()
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_ai_providers.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'app.core.ai'`

- [ ] **Step 3: Create `backend/app/core/ai/__init__.py`** (empty file)

- [ ] **Step 4: Create `backend/app/core/ai/base.py`**

```python
"""AI Provider Protocol definitions — no concrete implementations here."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class AIProvider(Protocol):
    """Protocol for LLM reply generation."""

    async def generate_reply(self, system: str, context: str, user_msg: str) -> str:
        """Generate a reply given system prompt, retrieved context, and user message."""
        ...


@runtime_checkable
class EmbedProvider(Protocol):
    """Protocol for text embedding."""

    async def embed(self, text: str) -> list[float]:
        """Return embedding vector for given text."""
        ...
```

- [ ] **Step 5: Create `backend/app/core/ai/claude.py`**

```python
"""Anthropic Claude implementation of AIProvider."""
import logging

from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024


class ClaudeProvider:
    """Uses Anthropic claude-sonnet-4-6 to generate replies."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    async def generate_reply(self, system: str, context: str, user_msg: str) -> str:
        user_content = f"Context:\n{context}\n\n---\nViewer comment: {user_msg}"
        message = await self._client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        reply = message.content[0].text
        logger.debug("Claude reply: %s", reply[:80])
        return reply
```

- [ ] **Step 6: Create `backend/app/core/ai/openai_llm.py`**

```python
"""OpenAI chat completions implementation of AIProvider."""
import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"
MAX_TOKENS = 1024


class OpenAILLMProvider:
    """Uses OpenAI gpt-4o-mini to generate replies."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

    async def generate_reply(self, system: str, context: str, user_msg: str) -> str:
        user_content = f"Context:\n{context}\n\n---\nViewer comment: {user_msg}"
        response = await self._client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        )
        reply = response.choices[0].message.content or ""
        logger.debug("OpenAI reply: %s", reply[:80])
        return reply
```

- [ ] **Step 7: Create `backend/app/core/ai/openai_embed.py`**

```python
"""OpenAI text-embedding-3-small implementation of EmbedProvider."""
import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

EMBED_MODEL = "text-embedding-3-small"


class OpenAIEmbedProvider:
    """Uses OpenAI text-embedding-3-small to embed text."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=EMBED_MODEL,
            input=text,
        )
        embedding = response.data[0].embedding
        logger.debug("Embedded %d chars → %d dims", len(text), len(embedding))
        return embedding
```

- [ ] **Step 8: Create `backend/app/core/ai/factory.py`**

```python
"""Factory functions to get configured AI providers from settings."""
from app.config import get_settings
from app.core.ai.claude import ClaudeProvider
from app.core.ai.openai_embed import OpenAIEmbedProvider
from app.core.ai.openai_llm import OpenAILLMProvider


def get_reply_provider():
    """Return configured reply provider based on AI_REPLY_PROVIDER setting."""
    settings = get_settings()
    provider_name = settings.ai_reply_provider.lower()

    if provider_name == "claude":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when AI_REPLY_PROVIDER=claude")
        return ClaudeProvider(api_key=settings.anthropic_api_key)

    if provider_name == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when AI_REPLY_PROVIDER=openai")
        return OpenAILLMProvider(api_key=settings.openai_api_key)

    raise ValueError(f"Unsupported AI_REPLY_PROVIDER: {provider_name!r}. Use 'claude' or 'openai'.")


def get_embed_provider():
    """Return configured embed provider (always OpenAI in v1)."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for embeddings")
    return OpenAIEmbedProvider(api_key=settings.openai_api_key)
```

- [ ] **Step 9: Run tests**

```bash
cd backend && pytest tests/test_ai_providers.py -v
```

Expected: 6 tests PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/core/ai/ backend/tests/test_ai_providers.py
git commit -m "feat: AI provider abstraction — Claude, OpenAI LLM, OpenAI embed, factory"
```

---

## Task 3: ChromaDB Retriever

**Files:**
- Create: `backend/app/core/rag/__init__.py`
- Create: `backend/app/core/rag/retriever.py`
- Create: `backend/tests/test_retriever.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_retriever.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_retriever.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError: No module named 'app.core.rag'`

- [ ] **Step 3: Create `backend/app/core/rag/__init__.py`** (empty)

- [ ] **Step 4: Create `backend/app/core/rag/retriever.py`**

```python
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
    collection.upsert(
        ids=[chunk_id],
        embeddings=[embedding],
        documents=[content],
        metadatas=[metadata],
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
```

- [ ] **Step 5: Run tests**

```bash
cd backend && pytest tests/test_retriever.py -v
```

Expected: 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/rag/__init__.py backend/app/core/rag/retriever.py backend/tests/test_retriever.py
git commit -m "feat: ChromaDB retriever — lazy client, add/delete/query per seller"
```

---

## Task 4: Comment Filter (Blacklist + Intent Detection + Cooldown)

**Files:**
- Create: `backend/app/core/rag/filter.py`
- Create: `backend/tests/test_filter.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_filter.py`:

```python
"""Tests for comment filter — blacklist, intent detection, per-user cooldown."""
import time

import pytest

DEFAULT_SETTINGS = {
    "tone": "friendly",
    "blacklist_keywords": ["spam", "xấu"],
    "reply_delay_min": 5,
    "reply_delay_max": 15,
    "user_cooldown_seconds": 60,
    "max_replies_per_session": 500,
    "auto_reply_enabled": True,
}


def make_filter(settings=None):
    from app.core.rag.filter import CommentFilter
    return CommentFilter(settings or DEFAULT_SETTINGS)


# --- Blacklist ---

def test_blacklist_blocks_comment():
    f = make_filter()
    result = f.check("user1", "đây là spam lắm")
    assert result.skip is True
    assert result.reason == "blacklist"


def test_blacklist_case_insensitive():
    f = make_filter()
    result = f.check("user1", "SPAM này")
    assert result.skip is True


def test_blacklist_allows_clean_comment():
    f = make_filter()
    result = f.check("user1", "Giá bao nhiêu vậy?")
    assert result.skip is False


# --- Intent ---

def test_detect_product_inquiry():
    from app.core.rag.filter import detect_intent
    assert detect_intent("Giá bao nhiêu ạ?") == "product_inquiry"
    assert detect_intent("còn hàng không shop?") == "product_inquiry"
    assert detect_intent("ship ra HN không?") == "product_inquiry"


def test_detect_greeting():
    from app.core.rag.filter import detect_intent
    assert detect_intent("hello shop") == "greeting"
    assert detect_intent("Chào shop ạ") == "greeting"


def test_detect_unknown_intent():
    from app.core.rag.filter import detect_intent
    assert detect_intent("oke") == "unknown"


# --- Cooldown ---

def test_cooldown_blocks_repeat_within_window():
    f = make_filter({"blacklist_keywords": [], "user_cooldown_seconds": 60, "auto_reply_enabled": True})
    f.update_cooldown("user1")
    result = f.check("user1", "Giá bao nhiêu?")
    assert result.skip is True
    assert result.reason == "cooldown"


def test_cooldown_allows_after_expiry():
    f = make_filter({"blacklist_keywords": [], "user_cooldown_seconds": 1, "auto_reply_enabled": True})
    f.update_cooldown("user1")
    time.sleep(1.1)
    result = f.check("user1", "Giá bao nhiêu?")
    assert result.skip is False


def test_cooldown_allows_new_user():
    f = make_filter()
    result = f.check("brand-new-user", "Sản phẩm còn hàng không?")
    assert result.skip is False


# --- auto_reply_enabled ---

def test_auto_reply_disabled_blocks_all():
    settings = {**DEFAULT_SETTINGS, "auto_reply_enabled": False}
    f = make_filter(settings)
    result = f.check("user1", "Giá bao nhiêu?")
    assert result.skip is True
    assert result.reason == "auto_reply_disabled"
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_filter.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError: No module named 'app.core.rag.filter'`

- [ ] **Step 3: Create `backend/app/core/rag/filter.py`**

```python
"""Comment filter: blacklist keywords, intent detection, per-user cooldown."""
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Vietnamese e-commerce intent keywords
_INTENT_KEYWORDS: dict[str, list[str]] = {
    "product_inquiry": [
        "giá", "bao nhiêu", "mua", "đặt hàng", "order", "ship", "giao hàng",
        "giao", "size", "màu", "chất liệu", "còn hàng", "hết hàng", "mẫu",
        "sản phẩm", "hàng", "thanh toán", "cod", "chuyển khoản", "freeship",
        "discount", "giảm giá", "khuyến mãi", "tặng", "bộ", "set",
    ],
    "greeting": [
        "hello", "hi", "chào", "alo", "hey", "xin chào", "shop ơi",
    ],
}


def detect_intent(text: str) -> str:
    """Return detected intent: 'product_inquiry' | 'greeting' | 'unknown'."""
    text_lower = text.lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return intent
    return "unknown"


@dataclass
class FilterResult:
    skip: bool
    reason: str | None = None  # "blacklist" | "cooldown" | "auto_reply_disabled" | None


@dataclass
class CommentFilter:
    """Stateful filter — holds per-user cooldown timestamps for a session."""

    _settings: dict[str, Any]
    _cooldown_map: dict[str, float] = field(default_factory=dict)

    def check(self, user_id: str, text: str) -> FilterResult:
        """Return FilterResult(skip=True, reason=...) if comment should be skipped."""
        # 1. auto_reply_enabled gate
        if not self._settings.get("auto_reply_enabled", True):
            return FilterResult(skip=True, reason="auto_reply_disabled")

        # 2. Blacklist
        blacklist = self._settings.get("blacklist_keywords", [])
        text_lower = text.lower()
        if any(kw.lower() in text_lower for kw in blacklist):
            logger.debug("Blacklist hit for user %s: %s", user_id, text[:40])
            return FilterResult(skip=True, reason="blacklist")

        # 3. Per-user cooldown
        cooldown_secs = self._settings.get("user_cooldown_seconds", 60)
        last_reply = self._cooldown_map.get(user_id)
        if last_reply is not None and (time.time() - last_reply) < cooldown_secs:
            logger.debug("Cooldown hit for user %s", user_id)
            return FilterResult(skip=True, reason="cooldown")

        return FilterResult(skip=False)

    def update_cooldown(self, user_id: str) -> None:
        """Record that we replied to this user right now."""
        self._cooldown_map[user_id] = time.time()
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_filter.py -v
```

Expected: 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/rag/filter.py backend/tests/test_filter.py
git commit -m "feat: comment filter — blacklist, intent detection, per-user cooldown"
```

---

## Task 5: RAG Pipeline Orchestration

**Files:**
- Create: `backend/app/core/rag/pipeline.py`
- Create: `backend/tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_pipeline.py`:

```python
"""Tests for RAG pipeline — all external deps mocked."""
from unittest.mock import AsyncMock

import pytest

DEFAULT_SETTINGS = {
    "tone": "friendly",
    "blacklist_keywords": ["cấm"],
    "reply_delay_min": 0,
    "reply_delay_max": 0,
    "user_cooldown_seconds": 60,
    "max_replies_per_session": 500,
    "auto_reply_enabled": True,
}

SELLER_ID = "seller-001"


def make_pipeline(embed_result=None, query_result=None, reply_result="Dạ shop còn hàng ạ!"):
    from app.core.rag.pipeline import RAGPipeline

    mock_embed = AsyncMock(return_value=embed_result or [0.1] * 1536)
    mock_retriever = AsyncMock(return_value=query_result or [
        {"id": "chunk-1", "content": "Áo cotton giá 150k", "metadata": {}, "distance": 0.1},
    ])
    mock_ai = AsyncMock(return_value=reply_result)

    return RAGPipeline(
        seller_id=SELLER_ID,
        seller_settings=DEFAULT_SETTINGS,
        embed_fn=mock_embed,
        retrieve_fn=mock_retriever,
        generate_reply_fn=mock_ai,
    ), mock_embed, mock_retriever, mock_ai


async def test_pipeline_returns_reply_on_product_inquiry():
    """Normal comment: embed → retrieve → generate → return reply."""
    pipeline, mock_embed, mock_retriever, mock_ai = make_pipeline()
    result = await pipeline.process("user1", "Giá bao nhiêu?")

    assert result.skipped is False
    assert result.reply == "Dạ shop còn hàng ạ!"
    assert result.intent == "product_inquiry"
    assert "chunk-1" in result.chunks_used
    mock_embed.assert_called_once_with("Giá bao nhiêu?")
    mock_retriever.assert_called_once()
    mock_ai.assert_called_once()


async def test_pipeline_skips_blacklisted_comment():
    """Blacklisted comment: skip immediately, no embed/retrieve/reply."""
    pipeline, mock_embed, mock_retriever, mock_ai = make_pipeline()
    result = await pipeline.process("user1", "spam cấm này")

    assert result.skipped is True
    assert result.intent == "skipped"
    assert result.reply is None
    mock_embed.assert_not_called()
    mock_retriever.assert_not_called()
    mock_ai.assert_not_called()


async def test_pipeline_skips_duplicate_user_within_cooldown():
    """Second comment from same user within cooldown window is skipped."""
    pipeline, _, _, _ = make_pipeline()
    await pipeline.process("user1", "Còn hàng không?")  # first — allowed

    pipeline2, mock_embed2, _, mock_ai2 = make_pipeline()
    # Transfer cooldown state
    pipeline2._filter._cooldown_map = pipeline._filter._cooldown_map
    result = await pipeline2.process("user1", "Ship đi tỉnh không?")  # second — blocked

    assert result.skipped is True
    assert result.skip_reason == "cooldown"


async def test_pipeline_includes_system_prompt_tone():
    """System prompt passed to AI includes the seller's configured tone."""
    pipeline, _, _, mock_ai = make_pipeline()
    await pipeline.process("user1", "Giá bao nhiêu?")

    call_kwargs = mock_ai.call_args.kwargs
    assert "friendly" in call_kwargs.get("system", "")


async def test_pipeline_empty_retriever_still_replies():
    """When no chunks are found, AI is still called (with empty context)."""
    pipeline, _, _, mock_ai = make_pipeline(query_result=[])
    result = await pipeline.process("user1", "Còn hàng không?")

    assert result.skipped is False
    assert result.chunks_used == []
    mock_ai.assert_called_once()
    call_kwargs = mock_ai.call_args.kwargs
    assert call_kwargs["context"] == ""
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_pipeline.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError: No module named 'app.core.rag.pipeline'`

- [ ] **Step 3: Create `backend/app/core/rag/pipeline.py`**

```python
"""RAG Pipeline — orchestrates filter → embed → retrieve → prompt → reply."""
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from app.core.rag.filter import CommentFilter, detect_intent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """\
Bạn là AI assistant hỗ trợ bán hàng trên TikTok Live. Nhiệm vụ của bạn là trả lời \
câu hỏi từ người xem livestream dựa trên thông tin sản phẩm được cung cấp.

Quy tắc:
- Luôn trả lời bằng tiếng Việt
- Ngắn gọn, thân thiện (tối đa 2-3 câu)
- Chỉ dùng thông tin trong Context, không bịa đặt
- Nếu không có thông tin phù hợp, nói "Để em hỏi lại và phản hồi sau nhé ạ!"
- Tone: {tone}"""


@dataclass
class RAGResult:
    intent: str
    reply: str | None
    chunks_used: list[str]
    skipped: bool
    skip_reason: str | None = None


@dataclass
class RAGPipeline:
    """
    Orchestrates the full RAG comment-reply flow.

    Inject dependencies via constructor to keep this testable without
    real API calls or a running ChromaDB instance.
    """

    seller_id: str
    seller_settings: dict[str, Any]
    embed_fn: Callable[[str], Awaitable[list[float]]]
    retrieve_fn: Callable[[str, list[float], int], Awaitable[list[dict]]]
    generate_reply_fn: Callable[..., Awaitable[str]]
    _filter: CommentFilter = field(init=False)

    def __post_init__(self) -> None:
        self._filter = CommentFilter(self.seller_settings)

    async def process(self, user_id: str, comment: str) -> RAGResult:
        """Process one comment through the full pipeline."""
        # 1. Filter
        filter_result = self._filter.check(user_id, comment)
        if filter_result.skip:
            logger.info("Comment skipped (reason=%s): %s", filter_result.reason, comment[:40])
            return RAGResult(
                intent="skipped",
                reply=None,
                chunks_used=[],
                skipped=True,
                skip_reason=filter_result.reason,
            )

        # 2. Detect intent
        intent = detect_intent(comment)

        # 3. Embed comment
        embedding = await self.embed_fn(comment)

        # 4. Retrieve top-3 chunks
        chunks = await self.retrieve_fn(self.seller_id, embedding, 3)

        # 5. Build context and system prompt
        context = "\n\n".join(c["content"] for c in chunks)
        system = SYSTEM_PROMPT_TEMPLATE.format(
            tone=self.seller_settings.get("tone", "friendly")
        )

        # 6. Generate reply
        reply = await self.generate_reply_fn(
            system=system,
            context=context,
            user_msg=comment,
        )

        # 7. Record cooldown
        self._filter.update_cooldown(user_id)

        logger.info("Reply for %s (intent=%s): %s", user_id, intent, reply[:60])
        return RAGResult(
            intent=intent,
            reply=reply,
            chunks_used=[c["id"] for c in chunks],
            skipped=False,
        )
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_pipeline.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/rag/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat: RAG pipeline — filter → embed → retrieve → prompt → reply"
```

---

## Task 6: Knowledge Base API + Schemas

**Files:**
- Create: `backend/app/schemas/knowledge.py`
- Create: `backend/app/api/v1/knowledge.py`
- Create: `backend/tests/test_knowledge_api.py`
- Modify: `backend/app/main.py` (include knowledge router)

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_knowledge_api.py`:

```python
"""Integration tests for knowledge base CRUD API."""
from unittest.mock import AsyncMock, patch

import pytest

# Use seller_id consistent across tests
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


async def test_create_knowledge_chunk(client, seller):
    """POST /api/v1/knowledge/ creates chunk and triggers embed."""
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        resp = await client.post("/api/v1/knowledge/", json={
            "seller_id": SELLER_ID,
            "content": "Áo cotton giá 150k",
            "category": "product",
            "metadata": {"product_name": "Áo Cotton"},
        })

    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Áo cotton giá 150k"
    assert data["seller_id"] == SELLER_ID
    assert "id" in data


async def test_list_knowledge_chunks(client, seller):
    """GET /api/v1/knowledge/?seller_id=... returns paginated chunks."""
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        await client.post("/api/v1/knowledge/", json={
            "seller_id": SELLER_ID,
            "content": "Sản phẩm A",
            "category": "faq",
            "metadata": {},
        })

    resp = await client.get(f"/api/v1/knowledge/?seller_id={SELLER_ID}&page=1&limit=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


async def test_update_knowledge_chunk(client, seller):
    """PUT /api/v1/knowledge/{id} updates content and sets needs_reembed=True."""
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        create_resp = await client.post("/api/v1/knowledge/", json={
            "seller_id": SELLER_ID,
            "content": "Original content",
            "category": "faq",
            "metadata": {},
        })
    chunk_id = create_resp.json()["id"]

    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock) as mock_embed:
        resp = await client.put(f"/api/v1/knowledge/{chunk_id}", json={
            "content": "Updated content",
        })

    assert resp.status_code == 200
    assert resp.json()["content"] == "Updated content"
    # Background re-embed triggered
    mock_embed.assert_called_once()


async def test_delete_knowledge_chunk(client, seller):
    """DELETE /api/v1/knowledge/{id} removes chunk from DB and ChromaDB."""
    with patch("app.api.v1.knowledge.embed_and_store", new_callable=AsyncMock):
        create_resp = await client.post("/api/v1/knowledge/", json={
            "seller_id": SELLER_ID,
            "content": "To delete",
            "category": "faq",
            "metadata": {},
        })
    chunk_id = create_resp.json()["id"]

    with patch("app.core.rag.retriever.delete_chunk", new_callable=AsyncMock):
        resp = await client.delete(f"/api/v1/knowledge/{chunk_id}")

    assert resp.status_code == 204


async def test_list_returns_empty_for_unknown_seller(client):
    """GET /api/v1/knowledge/ returns empty list for unknown seller."""
    resp = await client.get("/api/v1/knowledge/?seller_id=unknown-seller&page=1&limit=20")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_delete_not_found(client, seller):
    """DELETE on non-existent chunk returns 404."""
    with patch("app.core.rag.retriever.delete_chunk", new_callable=AsyncMock):
        resp = await client.delete("/api/v1/knowledge/non-existent-id")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_knowledge_api.py -v 2>&1 | head -15
```

Expected: `404 Not Found` or import errors — tests should fail.

- [ ] **Step 3: Create `backend/app/schemas/knowledge.py`**

```python
"""Pydantic schemas for Knowledge Base API."""
from typing import Any
from pydantic import BaseModel

from app.models.knowledge import KnowledgeCategory


class KnowledgeChunkCreate(BaseModel):
    seller_id: str
    content: str
    category: KnowledgeCategory = KnowledgeCategory.FAQ
    metadata: dict[str, Any] = {}


class KnowledgeChunkUpdate(BaseModel):
    content: str | None = None
    category: KnowledgeCategory | None = None
    metadata: dict[str, Any] | None = None


class KnowledgeChunkResponse(BaseModel):
    id: str
    seller_id: str
    content: str
    category: KnowledgeCategory
    metadata: dict[str, Any] = {}
    needs_reembed: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, obj) -> "KnowledgeChunkResponse":
        return cls(
            id=obj.id,
            seller_id=obj.seller_id,
            content=obj.content,
            category=obj.category,
            metadata=obj.metadata_,
            needs_reembed=obj.needs_reembed,
        )


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeChunkResponse]
    total: int
    page: int
    limit: int
```

- [ ] **Step 4: Create `backend/app/api/v1/knowledge.py`**

```python
"""Knowledge Base CRUD API."""
import csv
import io
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai.factory import get_embed_provider
from app.core.rag import retriever
from app.database import get_db, get_session_factory
from app.models.knowledge import KnowledgeChunk, KnowledgeCategory
from app.schemas.knowledge import (
    KnowledgeChunkCreate,
    KnowledgeChunkResponse,
    KnowledgeChunkUpdate,
    KnowledgeListResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

MAX_UPLOAD_ROWS = 500


async def embed_and_store(chunk_id: str, seller_id: str) -> None:
    """Background task: embed chunk content and upsert into ChromaDB."""
    async with get_session_factory()() as db:
        chunk = await db.get(KnowledgeChunk, chunk_id)
        if chunk is None or not chunk.needs_reembed:
            return
        try:
            embed_provider = get_embed_provider()
            embedding = await embed_provider.embed(chunk.content)
            await retriever.add_chunk(
                seller_id=seller_id,
                chunk_id=chunk.id,
                content=chunk.content,
                embedding=embedding,
                metadata={"category": chunk.category.value, **chunk.metadata_},
            )
            chunk.needs_reembed = False
            await db.commit()
            logger.info("Embedded chunk %s", chunk_id)
        except Exception:
            logger.exception("Failed to embed chunk %s", chunk_id)


@router.post("/", response_model=KnowledgeChunkResponse, status_code=201)
async def create_chunk(
    body: KnowledgeChunkCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    chunk = KnowledgeChunk(
        seller_id=body.seller_id,
        content=body.content,
        category=body.category,
        metadata_=body.metadata,
        needs_reembed=True,
    )
    db.add(chunk)
    await db.commit()
    await db.refresh(chunk)
    background_tasks.add_task(embed_and_store, chunk.id, body.seller_id)
    return KnowledgeChunkResponse.from_orm_model(chunk)


@router.get("/", response_model=KnowledgeListResponse)
async def list_chunks(
    seller_id: str,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    count_result = await db.execute(
        select(func.count()).where(KnowledgeChunk.seller_id == seller_id)
    )
    total = count_result.scalar() or 0

    items_result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.seller_id == seller_id)
        .offset(offset)
        .limit(limit)
    )
    items = items_result.scalars().all()

    return KnowledgeListResponse(
        items=[KnowledgeChunkResponse.from_orm_model(c) for c in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.put("/{chunk_id}", response_model=KnowledgeChunkResponse)
async def update_chunk(
    chunk_id: str,
    body: KnowledgeChunkUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    chunk = await db.get(KnowledgeChunk, chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")

    if body.content is not None:
        chunk.content = body.content
        chunk.needs_reembed = True
    if body.category is not None:
        chunk.category = body.category
        chunk.needs_reembed = True
    if body.metadata is not None:
        chunk.metadata_ = body.metadata

    await db.commit()
    await db.refresh(chunk)

    if chunk.needs_reembed:
        background_tasks.add_task(embed_and_store, chunk.id, chunk.seller_id)

    return KnowledgeChunkResponse.from_orm_model(chunk)


@router.delete("/{chunk_id}", status_code=204)
async def delete_chunk_endpoint(
    chunk_id: str,
    db: AsyncSession = Depends(get_db),
):
    chunk = await db.get(KnowledgeChunk, chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")

    await retriever.delete_chunk(chunk.seller_id, chunk_id)
    await db.delete(chunk)
    await db.commit()


@router.post("/upload")
async def upload_knowledge(
    seller_id: str,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Bulk import from CSV. Columns: content (required), category (optional), + any metadata cols."""
    filename = file.filename or ""
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content_bytes = await file.read()
    text = content_bytes.decode("utf-8-sig")  # handles BOM
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if len(rows) > MAX_UPLOAD_ROWS:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum {MAX_UPLOAD_ROWS} rows (got {len(rows)})",
        )

    if not rows or "content" not in (rows[0].keys() if rows else []):
        raise HTTPException(status_code=400, detail="CSV must have a 'content' column")

    chunks = []
    for row in rows:
        raw_content = row.get("content", "").strip()
        if not raw_content:
            continue

        raw_category = row.get("category", "faq").strip().lower()
        try:
            category = KnowledgeCategory(raw_category)
        except ValueError:
            category = KnowledgeCategory.FAQ

        metadata: dict[str, Any] = {
            k: v for k, v in row.items() if k not in ("content", "category") and v
        }

        chunk = KnowledgeChunk(
            seller_id=seller_id,
            content=raw_content,
            category=category,
            metadata_=metadata,
            needs_reembed=True,
        )
        db.add(chunk)
        chunks.append(chunk)

    await db.commit()
    for chunk in chunks:
        await db.refresh(chunk)
        background_tasks.add_task(embed_and_store, chunk.id, seller_id)

    return {"count": len(chunks), "message": "Chunks created, embedding in progress"}
```

- [ ] **Step 5: Update `backend/app/main.py` to include knowledge router**

Open `backend/app/main.py`. After the existing router imports at the bottom, add:

```python
from app.api.v1.knowledge import router as knowledge_router  # noqa: E402
app.include_router(knowledge_router)
```

- [ ] **Step 6: Run tests**

```bash
cd backend && pytest tests/test_knowledge_api.py -v
```

Expected: 6 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/knowledge.py backend/app/api/v1/knowledge.py \
        backend/app/main.py backend/tests/test_knowledge_api.py
git commit -m "feat: Knowledge Base CRUD API — create, list, update, delete, bulk upload"
```

---

## Task 7: Settings API + Schemas

**Files:**
- Create: `backend/app/schemas/settings.py`
- Create: `backend/app/api/v1/settings.py`
- Create: `backend/tests/test_settings_api.py`
- Modify: `backend/app/main.py` (include settings router)

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_settings_api.py`:

```python
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


async def test_get_settings(client, seller):
    """GET /api/v1/settings/?seller_id=... returns current bot settings."""
    resp = await client.get(f"/api/v1/settings/?seller_id={SELLER_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tone"] == "friendly"
    assert "blacklist_keywords" in data
    assert "auto_reply_enabled" in data


async def test_update_settings(client, seller):
    """PUT /api/v1/settings/ updates bot_settings JSON."""
    resp = await client.put(f"/api/v1/settings/?seller_id={SELLER_ID}", json={
        "tone": "professional",
        "user_cooldown_seconds": 30,
        "auto_reply_enabled": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["tone"] == "professional"
    assert data["user_cooldown_seconds"] == 30
    assert data["auto_reply_enabled"] is False


async def test_update_settings_merges_not_replaces(client, seller):
    """PUT only updates provided fields, preserves others."""
    # Set initial
    await client.put(f"/api/v1/settings/?seller_id={SELLER_ID}", json={
        "tone": "friendly",
        "reply_delay_min": 5,
    })
    # Update only tone
    resp = await client.put(f"/api/v1/settings/?seller_id={SELLER_ID}", json={
        "tone": "casual",
    })
    data = resp.json()
    assert data["tone"] == "casual"
    assert data["reply_delay_min"] == 5  # preserved


async def test_test_reply(client, seller):
    """POST /api/v1/settings/test-reply returns a preview reply without sending to TikTok."""
    with (
        patch("app.api.v1.settings.get_embed_provider") as mock_embed_factory,
        patch("app.api.v1.settings.retriever.query", new_callable=AsyncMock) as mock_query,
        patch("app.api.v1.settings.get_reply_provider") as mock_reply_factory,
    ):
        mock_embed_provider = AsyncMock()
        mock_embed_provider.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_factory.return_value = mock_embed_provider

        mock_query.return_value = [{"id": "c1", "content": "Áo giá 150k", "metadata": {}, "distance": 0.1}]

        mock_reply_provider = AsyncMock()
        mock_reply_provider.generate_reply = AsyncMock(return_value="Dạ giá 150k ạ!")
        mock_reply_factory.return_value = mock_reply_provider

        resp = await client.post("/api/v1/settings/test-reply", json={
            "seller_id": SELLER_ID,
            "comment": "Giá bao nhiêu?",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"] == "Dạ giá 150k ạ!"
    assert "intent" in data
    assert "chunks_used" in data


async def test_get_settings_not_found(client):
    """GET settings for unknown seller returns 404."""
    resp = await client.get("/api/v1/settings/?seller_id=unknown")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_settings_api.py -v 2>&1 | head -15
```

Expected: 404 errors or import errors.

- [ ] **Step 3: Create `backend/app/schemas/settings.py`**

```python
"""Pydantic schemas for Settings API."""
from typing import Any
from pydantic import BaseModel


class BotSettingsUpdate(BaseModel):
    """All fields optional — PUT merges into existing settings."""
    tone: str | None = None
    blacklist_keywords: list[str] | None = None
    reply_delay_min: int | None = None
    reply_delay_max: int | None = None
    user_cooldown_seconds: int | None = None
    max_replies_per_session: int | None = None
    auto_reply_enabled: bool | None = None


class BotSettingsResponse(BaseModel):
    tone: str
    blacklist_keywords: list[str]
    reply_delay_min: int
    reply_delay_max: int
    user_cooldown_seconds: int
    max_replies_per_session: int
    auto_reply_enabled: bool


class TestReplyRequest(BaseModel):
    seller_id: str
    comment: str


class TestReplyResponse(BaseModel):
    reply: str
    intent: str
    chunks_used: list[str]
```

- [ ] **Step 4: Create `backend/app/api/v1/settings.py`**

```python
"""Settings API — get/update bot settings, test-reply preview."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai.factory import get_embed_provider, get_reply_provider
from app.core.rag import retriever
from app.core.rag.filter import detect_intent
from app.database import get_db
from app.models.seller import Seller
from app.schemas.settings import BotSettingsResponse, BotSettingsUpdate, TestReplyRequest, TestReplyResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


async def _get_seller(seller_id: str, db: AsyncSession) -> Seller:
    seller = await db.get(Seller, seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")
    return seller


@router.get("/", response_model=BotSettingsResponse)
async def get_settings(seller_id: str, db: AsyncSession = Depends(get_db)):
    seller = await _get_seller(seller_id, db)
    return BotSettingsResponse(**seller.bot_settings)


@router.put("/", response_model=BotSettingsResponse)
async def update_settings(
    seller_id: str,
    body: BotSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    seller = await _get_seller(seller_id, db)

    # Merge: only update fields that were explicitly provided
    updated = dict(seller.bot_settings)
    patch = body.model_dump(exclude_none=True)
    updated.update(patch)
    seller.bot_settings = updated

    await db.commit()
    await db.refresh(seller)
    return BotSettingsResponse(**seller.bot_settings)


@router.post("/test-reply", response_model=TestReplyResponse)
async def test_reply(body: TestReplyRequest, db: AsyncSession = Depends(get_db)):
    """Run the full RAG pipeline for a comment and return the preview reply.
    Does NOT send anything to TikTok."""
    seller = await _get_seller(body.seller_id, db)
    settings = seller.bot_settings

    from app.core.rag.pipeline import SYSTEM_PROMPT_TEMPLATE

    intent = detect_intent(body.comment)

    embed_provider = get_embed_provider()
    embedding = await embed_provider.embed(body.comment)

    chunks = await retriever.query(body.seller_id, embedding, n_results=3)
    context = "\n\n".join(c["content"] for c in chunks)
    system = SYSTEM_PROMPT_TEMPLATE.format(tone=settings.get("tone", "friendly"))

    reply_provider = get_reply_provider()
    reply = await reply_provider.generate_reply(system=system, context=context, user_msg=body.comment)

    return TestReplyResponse(
        reply=reply,
        intent=intent,
        chunks_used=[c["id"] for c in chunks],
    )
```

- [ ] **Step 5: Update `backend/app/main.py` to include settings router**

Add after knowledge router:

```python
from app.api.v1.settings import router as settings_router  # noqa: E402
app.include_router(settings_router)
```

- [ ] **Step 6: Run tests**

```bash
cd backend && pytest tests/test_settings_api.py -v
```

Expected: 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/settings.py backend/app/api/v1/settings.py \
        backend/app/main.py backend/tests/test_settings_api.py
git commit -m "feat: Settings API — get/update bot settings, test-reply preview"
```

---

## Task 8: Wire Sessions Start/Stop with RAG Pipeline

**Files:**
- Modify: `backend/app/api/v1/sessions.py`
- Modify: `backend/tests/conftest.py` (reset new global state)
- Create: `backend/tests/test_session_wiring.py`

This is the biggest task — it wires the entire system together.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_session_wiring.py`:

```python
"""Integration tests for session start/stop/history wiring."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SELLER_ID = "wiring-seller-001"


@pytest.fixture
async def seller(db_session):
    from app.models.seller import Seller
    from app.core.crypto import encrypt

    s = Seller(
        name="Wiring Shop",
        tiktok_unique_id="@wiringshop",
        tiktok_session_id_encrypted=encrypt("sess-abc"),
        tiktok_target_idc_encrypted=encrypt("useast1a"),
    )
    s.id = SELLER_ID
    db_session.add(s)
    await db_session.commit()
    return s


async def test_start_session_creates_live_session(client, seller):
    """POST /api/v1/sessions/start creates LiveSession with ACTIVE status."""
    with (
        patch("app.api.v1.sessions.TikTokLiveClient") as mock_tiktok_cls,
        patch("app.api.v1.sessions.LiveListener") as mock_listener_cls,
        patch("app.api.v1.sessions.get_embed_provider") as mock_embed_factory,
        patch("app.api.v1.sessions.get_reply_provider") as mock_reply_factory,
        patch("asyncio.create_task"),
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

        resp = await client.post("/api/v1/sessions/start", json={
            "seller_id": SELLER_ID,
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["session"]["status"] == "active"


async def test_start_session_twice_returns_400(client, seller):
    """Cannot start a second session while one is already active."""
    with (
        patch("app.api.v1.sessions.TikTokLiveClient") as mock_tiktok_cls,
        patch("app.api.v1.sessions.LiveListener") as mock_listener_cls,
        patch("app.api.v1.sessions.get_embed_provider"),
        patch("app.api.v1.sessions.get_reply_provider"),
        patch("asyncio.create_task"),
    ):
        mock_client = MagicMock()
        mock_client.web = MagicMock()
        mock_tiktok_cls.return_value = mock_client
        mock_listener = MagicMock()
        mock_listener_cls.return_value = mock_listener

        await client.post("/api/v1/sessions/start", json={"seller_id": SELLER_ID})
        resp2 = await client.post("/api/v1/sessions/start", json={"seller_id": SELLER_ID})

    assert resp2.status_code == 400


async def test_stop_session(client, seller):
    """POST /api/v1/sessions/stop ends active session."""
    with (
        patch("app.api.v1.sessions.TikTokLiveClient") as mock_tiktok_cls,
        patch("app.api.v1.sessions.LiveListener") as mock_listener_cls,
        patch("app.api.v1.sessions.get_embed_provider"),
        patch("app.api.v1.sessions.get_reply_provider"),
        patch("asyncio.create_task"),
    ):
        mock_client = MagicMock()
        mock_client.web = MagicMock()
        mock_tiktok_cls.return_value = mock_client
        mock_listener = MagicMock()
        mock_listener.stop = AsyncMock()
        mock_listener_cls.return_value = mock_listener

        await client.post("/api/v1/sessions/start", json={"seller_id": SELLER_ID})

    resp = await client.post("/api/v1/sessions/stop")
    assert resp.status_code == 200


async def test_stop_when_no_active_session_returns_400(client):
    """POST /stop with no active session returns 400."""
    resp = await client.post("/api/v1/sessions/stop")
    assert resp.status_code == 400


async def test_history_returns_list(client, seller):
    """GET /api/v1/sessions/history returns list of past sessions."""
    from app.models.session import LiveSession, SessionStatus

    # Pre-populate a session
    from app.database import _get_session_factory
    from datetime import datetime, timezone

    # Use the db_session fixture approach indirectly via the client DB
    resp = await client.get("/api/v1/sessions/history?page=1&limit=20")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_session_wiring.py -v 2>&1 | head -20
```

Expected: `422 Unprocessable Entity` or `404` for start endpoint (not implemented yet).

- [ ] **Step 3: Update conftest.py to reset new global session state**

Open `backend/tests/conftest.py`. Update the `reset_session_state` fixture to reset all Plan 2 globals:

```python
@pytest.fixture(autouse=True)
def reset_session_state():
    """Reset all module-level session state between tests."""
    import app.api.v1.sessions as sessions_module
    sessions_module._active_session_id = None
    sessions_module._active_listener = None
    sessions_module._active_replier = None
    sessions_module._active_pipeline = None
    sessions_module._bot_paused = False
    sessions_module._reply_count = 0
    yield
    sessions_module._active_session_id = None
    sessions_module._active_listener = None
    sessions_module._active_replier = None
    sessions_module._active_pipeline = None
    sessions_module._bot_paused = False
    sessions_module._reply_count = 0
```

- [ ] **Step 4: Rewrite `backend/app/api/v1/sessions.py`**

Replace the entire file content:

```python
"""Live Session API — start/stop/status/history + full RAG wiring."""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from TikTokLive.client.client import TikTokLiveClient

from app.api.ws import broadcast
from app.core.ai.factory import get_embed_provider, get_reply_provider
from app.core.crypto import decrypt
from app.core.rag import retriever
from app.core.rag.pipeline import RAGPipeline
from app.core.tiktok.listener import LiveListener
from app.core.tiktok.replier import Replier
from app.database import get_db, get_session_factory
from app.models.message import MessageLog
from app.models.seller import Seller
from app.models.session import LiveSession, SessionStatus
from app.schemas.session import SessionResponse, SessionStartRequest, SessionStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

# ── Module-level single-seller state ────────────────────────────────────────
_active_session_id: str | None = None
_active_listener: LiveListener | None = None
_active_replier: Replier | None = None
_active_pipeline: RAGPipeline | None = None
_bot_paused: bool = False
_reply_count: int = 0


# ── Internal helpers ─────────────────────────────────────────────────────────

def _build_pipeline(seller: Seller) -> RAGPipeline:
    embed_provider = get_embed_provider()
    reply_provider = get_reply_provider()
    return RAGPipeline(
        seller_id=seller.id,
        seller_settings=seller.bot_settings,
        embed_fn=embed_provider.embed,
        retrieve_fn=retriever.query,
        generate_reply_fn=reply_provider.generate_reply,
    )


async def _handle_comment(user: str, text: str) -> None:
    """Background callback: filter → RAG → save → reply → broadcast."""
    global _reply_count

    if _bot_paused or _active_pipeline is None or _active_session_id is None:
        return

    max_replies = _active_pipeline.seller_settings.get("max_replies_per_session", 500)
    if _reply_count >= max_replies:
        logger.info("max_replies_per_session reached (%d), skipping", max_replies)
        return

    # Save incoming comment
    message_id: str | None = None
    async with get_session_factory()() as db:
        msg = MessageLog(
            session_id=_active_session_id,
            user_unique_id=user,
            comment=text,
            intent="unknown",
            chunks_used=[],
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        message_id = msg.id

    # Broadcast comment to dashboard
    await broadcast({"type": "comment", "message_id": message_id, "user": user, "content": text,
                     "timestamp": datetime.now(timezone.utc).isoformat()})

    # Run RAG pipeline
    result = await _active_pipeline.process(user, text)

    if result.skipped or result.reply is None:
        # Update intent/skip
        async with get_session_factory()() as db:
            msg = await db.get(MessageLog, message_id)
            if msg:
                msg.intent = result.intent
                await db.commit()
        return

    # Send reply via replier (with throttle)
    try:
        if _active_replier is not None:
            await _active_replier.send(result.reply)
        _reply_count += 1
    except Exception:
        logger.exception("Failed to send TikTok reply")

    # Persist reply
    async with get_session_factory()() as db:
        msg = await db.get(MessageLog, message_id)
        if msg:
            msg.reply = result.reply
            msg.intent = result.intent
            msg.chunks_used = result.chunks_used
            await db.commit()

    # Broadcast reply to dashboard
    await broadcast({"type": "reply", "message_id": message_id, "content": result.reply,
                     "intent": result.intent, "chunks_used": result.chunks_used})


async def _handle_disconnect() -> None:
    """Callback when TikTok stream ends or connection drops."""
    global _active_session_id

    logger.info("TikTok disconnect — marking session ended")
    if _active_session_id:
        async with get_session_factory()() as db:
            session = await db.get(LiveSession, _active_session_id)
            if session:
                session.status = SessionStatus.ENDED
                session.ended_at = datetime.now(timezone.utc)
                await db.commit()

    await broadcast({"type": "status", "connected": False})


# ── API Endpoints ─────────────────────────────────────────────────────────────

@router.post("/start", response_model=SessionStatusResponse)
async def start_session(
    body: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
):
    global _active_session_id, _active_listener, _active_replier, _active_pipeline
    global _bot_paused, _reply_count

    if _active_session_id is not None:
        raise HTTPException(status_code=400, detail="A session is already active. Stop it first.")

    seller = await db.get(Seller, body.seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")

    # Decrypt TikTok credentials
    session_id = decrypt(seller.tiktok_session_id_encrypted)
    target_idc = decrypt(seller.tiktok_target_idc_encrypted)

    # Build TikTok client
    tiktok_client = TikTokLiveClient(unique_id=seller.tiktok_unique_id)
    tiktok_client.web.set_session(session_id, target_idc)

    # Build components
    listener = LiveListener(tiktok_client)
    replier = Replier(
        web_client=tiktok_client.web,
        delay_min=float(seller.bot_settings.get("reply_delay_min", 5)),
        delay_max=float(seller.bot_settings.get("reply_delay_max", 15)),
    )
    pipeline = _build_pipeline(seller)

    # Register callbacks
    listener.on_comment(_handle_comment)
    listener.on_disconnect(_handle_disconnect)

    # Create DB session record
    live_session = LiveSession(seller_id=seller.id, status=SessionStatus.ACTIVE)
    db.add(live_session)
    await db.commit()
    await db.refresh(live_session)

    # Store state
    _active_session_id = live_session.id
    _active_listener = listener
    _active_replier = replier
    _active_pipeline = pipeline
    _bot_paused = False
    _reply_count = 0

    # Start listener in background (non-blocking)
    asyncio.create_task(listener.start())

    await broadcast({"type": "status", "connected": True, "room_id": None})
    logger.info("Session started: %s", live_session.id)

    return SessionStatusResponse(connected=True, session=SessionResponse.model_validate(live_session))


@router.post("/stop")
async def stop_session(db: AsyncSession = Depends(get_db)):
    global _active_session_id, _active_listener, _active_replier, _active_pipeline
    global _bot_paused, _reply_count

    if _active_session_id is None:
        raise HTTPException(status_code=400, detail="No active session")

    if _active_listener is not None:
        try:
            await _active_listener.stop()
        except Exception:
            logger.exception("Error stopping listener")

    session = await db.get(LiveSession, _active_session_id)
    if session:
        session.status = SessionStatus.ENDED
        session.ended_at = datetime.now(timezone.utc)
        await db.commit()

    _active_session_id = None
    _active_listener = None
    _active_replier = None
    _active_pipeline = None
    _bot_paused = False
    _reply_count = 0

    await broadcast({"type": "status", "connected": False})
    return {"message": "Session stopped"}


@router.get("/status", response_model=SessionStatusResponse)
async def get_status(db: AsyncSession = Depends(get_db)):
    if _active_session_id is None:
        return SessionStatusResponse(connected=False, session=None)

    result = await db.execute(
        select(LiveSession).where(LiveSession.id == _active_session_id)
    )
    session = result.scalar_one_or_none()
    if session is None or session.status != SessionStatus.ACTIVE:
        return SessionStatusResponse(connected=False, session=None)

    return SessionStatusResponse(connected=True, session=SessionResponse.model_validate(session))


@router.get("/history", response_model=list[SessionResponse])
async def get_history(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    result = await db.execute(
        select(LiveSession)
        .order_by(LiveSession.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    sessions = result.scalars().all()
    return [SessionResponse.model_validate(s) for s in sessions]
```

- [ ] **Step 5: Update `SessionStartRequest` schema** — it no longer needs `tiktok_unique_id` (we read it from Seller). Open `backend/app/schemas/session.py` and update:

```python
class SessionStartRequest(BaseModel):
    seller_id: str
    # tiktok_unique_id read from Seller record
```

- [ ] **Step 6: Run tests**

```bash
cd backend && pytest tests/test_session_wiring.py -v
```

Expected: 5 tests PASS

- [ ] **Step 7: Run full test suite to verify no regressions**

```bash
cd backend && pytest tests/ -v --tb=short
```

Expected: all tests pass (was 12, now should be ~28+)

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/v1/sessions.py backend/app/schemas/session.py \
        backend/tests/conftest.py backend/tests/test_session_wiring.py
git commit -m "feat: wire sessions start/stop with RAG pipeline — listener → filter → RAG → reply → WS"
```

---

## Task 9: WebSocket Command Handling + Final Integration

**Files:**
- Modify: `backend/app/api/ws.py`
- Modify: `backend/app/main.py` (register all routers)
- Create: no new test file — extend existing conftest + run full suite

- [ ] **Step 1: Update `backend/app/api/ws.py` to handle WS commands**

Replace the `# Command handling wired in Plan 2` comment block with full command handling:

```python
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

_connections: list[WebSocket] = []


async def broadcast(message: dict[str, Any]) -> None:
    """Send a message to all connected dashboard clients."""
    dead = []
    for ws in _connections:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.remove(ws)


@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    await websocket.accept()
    _connections.append(websocket)
    logger.info("Dashboard client connected (%d total)", len(_connections))
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from WS client, ignoring")
                continue

            msg_type = msg.get("type")
            logger.info("WS command received: %s", msg_type)

            if msg_type == "pause_bot":
                import app.api.v1.sessions as sessions_module
                sessions_module._bot_paused = True
                await broadcast({"type": "status", "paused": True})

            elif msg_type == "resume_bot":
                import app.api.v1.sessions as sessions_module
                sessions_module._bot_paused = False
                await broadcast({"type": "status", "paused": False})

            elif msg_type == "manual_reply":
                await _handle_manual_reply(msg)

    except WebSocketDisconnect:
        if websocket in _connections:
            _connections.remove(websocket)
        logger.info("Dashboard client disconnected (%d remaining)", len(_connections))
    except Exception:
        logger.exception("WebSocket error")
        if websocket in _connections:
            _connections.remove(websocket)


async def _handle_manual_reply(msg: dict) -> None:
    """Send a manual reply for a specific message_id via the active replier."""
    import app.api.v1.sessions as sessions_module
    from app.database import get_session_factory
    from app.models.message import MessageLog

    message_id = msg.get("message_id")
    content = msg.get("content", "").strip()

    if not message_id or not content:
        logger.warning("manual_reply missing message_id or content")
        return

    replier = sessions_module._active_replier
    if replier is None:
        await broadcast({"type": "error", "message": "No active session"})
        return

    try:
        await replier.send(content)
    except Exception as exc:
        logger.exception("manual_reply send failed")
        await broadcast({"type": "error", "message": str(exc)})
        return

    # Persist reply in DB
    async with get_session_factory()() as db:
        log = await db.get(MessageLog, message_id)
        if log:
            log.reply = content
            log.intent = "manual"
            await db.commit()

    await broadcast({"type": "reply", "message_id": message_id, "content": content,
                     "intent": "manual", "chunks_used": []})
```

- [ ] **Step 2: Update `/health` endpoint in `backend/app/main.py` to include ChromaDB + DB status**

The spec (Section 6) requires: `GET /health → { status, chroma, ai_provider, db }`. Replace the existing `health()` function:

```python
@app.get("/health")
async def health():
    settings = get_settings()
    results: dict = {
        "status": "ok",
        "ai_provider": settings.ai_reply_provider,
        "db": "unknown",
        "chroma": "unknown",
    }

    # Check DB
    try:
        from app.database import _get_engine
        async with _get_engine().connect() as conn:
            await conn.execute(__import__("sqlalchemy", fromlist=["text"]).text("SELECT 1"))
        results["db"] = "ok"
    except Exception as exc:
        results["db"] = f"error: {exc}"
        results["status"] = "degraded"

    # Check ChromaDB
    try:
        from app.core.rag.retriever import _get_client
        _get_client().heartbeat()
        results["chroma"] = "ok"
    except Exception as exc:
        results["chroma"] = f"error: {exc}"
        results["status"] = "degraded"

    return results
```

- [ ] **Step 3: Verify all routers are registered in `backend/app/main.py`**

The file should include these imports at the bottom (in order):

```python
from app.api.v1.sessions import router as sessions_router  # noqa: E402
app.include_router(sessions_router)

from app.api.v1.knowledge import router as knowledge_router  # noqa: E402
app.include_router(knowledge_router)

from app.api.v1.settings import router as settings_router  # noqa: E402
app.include_router(settings_router)

from app.api.ws import router as ws_router  # noqa: E402
app.include_router(ws_router)
```

- [ ] **Step 4: Run the full test suite**

```bash
cd backend && pytest tests/ -v --tb=short
```

Expected: all tests PASS (30+ tests)

- [ ] **Step 5: Check test coverage**

```bash
cd backend && pytest tests/ --cov=app --cov-report=term-missing --tb=short
```

Expected: coverage ≥ 75% across all modules

- [ ] **Step 6: Lint check**

```bash
cd backend && ruff check app/ tests/
```

Expected: no errors

- [ ] **Step 7: Manual smoke test (optional, requires real .env)**

Start the backend locally:
```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` — verify all routes appear:
- `/api/v1/sessions/start`
- `/api/v1/sessions/stop`
- `/api/v1/sessions/status`
- `/api/v1/sessions/history`
- `/api/v1/knowledge/` (GET, POST)
- `/api/v1/knowledge/{id}` (PUT, DELETE)
- `/api/v1/knowledge/upload`
- `/api/v1/settings/`
- `/api/v1/settings/test-reply`
- `/health`
- `/ws/monitor`

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/ws.py backend/app/main.py
git commit -m "feat: WS commands + health endpoint with chroma/db status"
```

- [ ] **Step 9: Final integration commit tag**

```bash
git tag plan2-complete
```

---

## Summary: What Plan 2 Delivers

After all 9 tasks:

| Component | Status |
|-----------|--------|
| AI Provider abstraction (`core/ai/`) | ✅ Claude + OpenAI reply, OpenAI embed, factory |
| ChromaDB retriever (`core/rag/retriever.py`) | ✅ Lazy client, upsert/delete/query per seller |
| Comment filter (`core/rag/filter.py`) | ✅ Blacklist, intent detection, per-user cooldown |
| RAG pipeline (`core/rag/pipeline.py`) | ✅ Full orchestration, injectable deps |
| Knowledge Base API | ✅ CRUD + bulk CSV upload + background embed |
| Settings API | ✅ Get/update + test-reply preview |
| Sessions start/stop | ✅ Full TikTok wiring → RAG → DB → WS broadcast |
| WebSocket commands | ✅ pause_bot / resume_bot / manual_reply |

**Next:** Plan 3 — Frontend (Next.js 14, Knowledge page, Monitor dashboard, Settings page)
