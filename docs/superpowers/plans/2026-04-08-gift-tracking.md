# Gift Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate TikTokLive `GiftEvent` to track gifts in real-time, auto-thank gifters via LLM, and surface gift/revenue analytics on the dashboard.

**Architecture:** Gift events flow through the existing RAG pipeline's new `process_gift()` method, which reuses `generate_reply_fn` and seller settings but skips embedding and retrieval. A new `GiftLog` model stores gift data, with WebSocket broadcasts for real-time dashboard updates.

**Tech Stack:** Python 3 / FastAPI / SQLAlchemy (async) / Alembic / Pydantic v2 / TikTokLive (vendored) / Next.js / TypeScript / Tailwind CSS / shadcn/ui

---

## File Structure

### Backend — New Files
- `backend/app/models/gift.py` — `GiftLog` SQLAlchemy model
- `backend/alembic/versions/<hash>_add_gift_logs_table.py` — Migration
- `backend/app/schemas/gift.py` — Pydantic schemas (`GiftLogResponse`, `GiftStats`, `TopGifter`, `GiftBreakdown`)
- `backend/tests/test_gift_model.py` — GiftLog model tests
- `backend/tests/test_gift_pipeline.py` — `process_gift()` unit tests
- `backend/tests/test_gift_listener.py` — Streak filtering + `_handle_gift` wiring tests
- `backend/tests/test_gift_api.py` — Session gifts endpoint + analytics gift_stats tests

### Backend — Modified Files
- `backend/app/models/__init__.py` — Export `GiftLog`
- `backend/app/models/session.py` — Add `gifts` relationship
- `backend/app/core/rag/pipeline.py` — Add `GiftReplyResult` dataclass + `process_gift()` method
- `backend/app/core/tiktok/listener.py` — Add `GiftEvent` handler, `GiftHandler` type, `on_gift()`
- `backend/app/api/v1/sessions.py` — Add `_handle_gift()`, register gift handler, add gifts endpoint
- `backend/app/api/v1/analytics.py` — Add `gift_stats` query + response
- `backend/app/schemas/analytics.py` — Add `GiftStats` to `AnalyticsResponse`
- `backend/tests/conftest.py` — Import `gift` model for `create_all`

### Frontend — New Files
- `frontend/components/monitor/GiftFeed.tsx` — Real-time gift feed component
- `frontend/components/analytics/GiftStats.tsx` — Gift stat cards + top gifters + gift breakdown

### Frontend — Modified Files
- `frontend/lib/api.ts` — Add gift types, `gift_stats` on `AnalyticsData`, `api.sessions.gifts()`
- `frontend/lib/ws.ts` — Add `gift` and `gift_reply` to `WSMessage` union
- `frontend/app/monitor/page.tsx` — 2-column layout with GiftFeed
- `frontend/app/analytics/page.tsx` — Render GiftStats component
- `frontend/hooks/useWebSocket.ts` — No changes needed (generic handler system)

---

## Discoveries from Previous Feature

- Python command is `python3` not `python`
- conftest.py uses temp file SQLite (not in-memory) and needs explicit model imports before `Base.metadata.create_all`
- bcrypt is used directly (not passlib)
- SQLite doesn't support ALTER constraints — use index
- `GiftEvent` fields: `event.user.unique_id`, `event.gift.name`, `event.gift.diamond_count`, `event.gift.streakable`, `event.repeat_count`, `event.repeat_end`, `event.streaking` (property), `event.value` (property)
- Streak check: `if event.gift.streakable and not event.streaking` → streak ended; `if not event.gift.streakable` → no streak possible. From `examples/gifts.py`.
- Frontend uses Next.js App Router with `"use client"` directives, shadcn/ui components, Tailwind CSS
- Frontend AGENTS.md note: "This is NOT the Next.js you know" — check `node_modules/next/dist/docs/` before writing code

---

### Task 1: GiftLog Model + Migration

**Files:**
- Create: `backend/app/models/gift.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/session.py:11-12,33`
- Modify: `backend/tests/conftest.py:15`
- Test: `backend/tests/test_gift_model.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_gift_model.py`:

```python
"""Tests for GiftLog model."""
import pytest
from app.models.gift import GiftLog
from app.models.session import LiveSession


@pytest.mark.asyncio
async def test_gift_log_creation(db_session, test_seller):
    """GiftLog can be created with all required fields."""
    session = LiveSession(seller_id=test_seller.id, status="active")
    db_session.add(session)
    await db_session.commit()

    gift = GiftLog(
        session_id=session.id,
        user_unique_id="viewer123",
        gift_name="Rose",
        diamond_count=1,
        repeat_count=5,
        total_diamonds=5,
        estimated_usd=0.025,
    )
    db_session.add(gift)
    await db_session.commit()
    await db_session.refresh(gift)

    assert gift.id is not None
    assert gift.gift_name == "Rose"
    assert gift.diamond_count == 1
    assert gift.repeat_count == 5
    assert gift.total_diamonds == 5
    assert gift.estimated_usd == pytest.approx(0.025)
    assert gift.thank_reply is None
    assert gift.created_at is not None


@pytest.mark.asyncio
async def test_gift_log_with_thank_reply(db_session, test_seller):
    """GiftLog thank_reply can be set after creation."""
    session = LiveSession(seller_id=test_seller.id, status="active")
    db_session.add(session)
    await db_session.commit()

    gift = GiftLog(
        session_id=session.id,
        user_unique_id="viewer456",
        gift_name="Lion",
        diamond_count=500,
        repeat_count=1,
        total_diamonds=500,
        estimated_usd=2.5,
        thank_reply="Cảm ơn bạn rất nhiều!",
    )
    db_session.add(gift)
    await db_session.commit()
    await db_session.refresh(gift)

    assert gift.thank_reply == "Cảm ơn bạn rất nhiều!"


@pytest.mark.asyncio
async def test_gift_log_session_relationship(db_session, test_seller):
    """GiftLog is accessible via LiveSession.gifts relationship."""
    session = LiveSession(seller_id=test_seller.id, status="active")
    db_session.add(session)
    await db_session.commit()

    gift = GiftLog(
        session_id=session.id,
        user_unique_id="viewer789",
        gift_name="Sunglasses",
        diamond_count=199,
        repeat_count=2,
        total_diamonds=398,
        estimated_usd=1.99,
    )
    db_session.add(gift)
    await db_session.commit()

    await db_session.refresh(session)
    # Access via relationship
    from sqlalchemy import select
    from app.models.gift import GiftLog as GL
    result = await db_session.execute(
        select(GL).where(GL.session_id == session.id)
    )
    gifts = result.scalars().all()
    assert len(gifts) == 1
    assert gifts[0].gift_name == "Sunglasses"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_gift_model.py -v` from `backend/`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.gift'`

- [ ] **Step 3: Create GiftLog model**

Create `backend/app/models/gift.py`:

```python
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.session import LiveSession


class GiftLog(Base):
    __tablename__ = "gift_logs"
    __table_args__ = (
        Index(
            "ix_gift_dedup",
            "session_id",
            "user_unique_id",
            "gift_name",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("live_sessions.id"), nullable=False)
    user_unique_id: Mapped[str] = mapped_column(String, nullable=False)
    gift_name: Mapped[str] = mapped_column(String, nullable=False)
    diamond_count: Mapped[int] = mapped_column(Integer, nullable=False)
    repeat_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_diamonds: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_usd: Mapped[float] = mapped_column(Float, nullable=False)
    thank_reply: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["LiveSession"] = relationship(back_populates="gifts")
```

- [ ] **Step 4: Update models/__init__.py to export GiftLog**

Add to `backend/app/models/__init__.py`:

```python
from app.models.gift import GiftLog
```

And add `"GiftLog"` to the `__all__` list.

- [ ] **Step 5: Add gifts relationship to LiveSession**

In `backend/app/models/session.py`, add `GiftLog` to the TYPE_CHECKING imports:

```python
if TYPE_CHECKING:
    from app.models.gift import GiftLog
    from app.models.message import MessageLog
    from app.models.seller import Seller
```

Add the relationship after line 33:

```python
    gifts: Mapped[list["GiftLog"]] = relationship(back_populates="session")
```

- [ ] **Step 6: Update conftest.py to import gift model**

In `backend/tests/conftest.py`, add after line 15:

```python
import app.models.gift  # noqa: F401
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_gift_model.py -v` from `backend/`
Expected: 3 tests PASS

- [ ] **Step 8: Generate Alembic migration**

Run from `backend/`:

```bash
python3 -m alembic revision --autogenerate -m "add gift_logs table"
```

Review the generated migration to ensure it only contains `create_table("gift_logs", ...)` and the `ix_gift_dedup` index. Remove any drift noise from other tables.

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/gift.py backend/app/models/__init__.py backend/app/models/session.py backend/tests/conftest.py backend/tests/test_gift_model.py backend/alembic/versions/*gift_logs*
git commit -m "feat: add GiftLog model with dedup index and Alembic migration"
```

---

### Task 2: Pydantic Schemas for Gifts

**Files:**
- Create: `backend/app/schemas/gift.py`
- Modify: `backend/app/schemas/analytics.py`

- [ ] **Step 1: Create gift schemas**

Create `backend/app/schemas/gift.py`:

```python
"""Pydantic schemas for gift tracking."""
from datetime import datetime

from pydantic import BaseModel


class GiftLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    session_id: str
    user_unique_id: str
    gift_name: str
    diamond_count: int
    repeat_count: int
    total_diamonds: int
    estimated_usd: float
    thank_reply: str | None
    created_at: datetime


class TopGifter(BaseModel):
    user: str
    total_diamonds: int
    gift_count: int


class GiftBreakdown(BaseModel):
    gift_name: str
    count: int
    total_diamonds: int


class GiftStats(BaseModel):
    total_gifts: int
    total_diamonds: int
    estimated_usd: float
    top_gifters: list[TopGifter]
    gift_breakdown: list[GiftBreakdown]
```

- [ ] **Step 2: Add gift_stats to AnalyticsResponse**

In `backend/app/schemas/analytics.py`, add import and field:

```python
from pydantic import BaseModel, Field
from app.schemas.gift import GiftStats


class AnalyticsResponse(BaseModel):
    total_sessions: int
    total_comments: int
    total_replies: int
    reply_rate: float  # 0-100
    intent_breakdown: dict[str, int] = Field(
        default_factory=dict, description="Intent label to count mapping"
    )
    sentiment_breakdown: dict[str, int] = Field(
        default_factory=dict, description="Sentiment label to count mapping"
    )
    unanswered_count: int
    gift_stats: GiftStats | None = None
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/gift.py backend/app/schemas/analytics.py
git commit -m "feat: add gift Pydantic schemas and gift_stats to AnalyticsResponse"
```

---

### Task 3: RAGPipeline.process_gift() Method

**Files:**
- Modify: `backend/app/core/rag/pipeline.py`
- Test: `backend/tests/test_gift_pipeline.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_gift_pipeline.py`:

```python
"""Tests for RAGPipeline.process_gift() method."""
import pytest
from unittest.mock import AsyncMock

from app.core.ai.base import LLMResult
from app.core.rag.pipeline import RAGPipeline, GiftReplyResult


@pytest.fixture
def mock_pipeline():
    """RAGPipeline with all dependencies mocked."""
    return RAGPipeline(
        seller_id="seller-1",
        seller_settings={"tone": "vui vẻ", "auto_reply_enabled": True},
        embed_fn=AsyncMock(return_value=[0.1] * 384),
        retrieve_fn=AsyncMock(return_value=[]),
        generate_reply_fn=AsyncMock(
            return_value=LLMResult(
                intent="gift_thank",
                sentiment="positive",
                reply="Cảm ơn bạn đã tặng quà!",
            )
        ),
        fetch_overrides_fn=AsyncMock(return_value=[]),
    )


@pytest.mark.asyncio
async def test_process_gift_returns_gift_reply_result(mock_pipeline):
    """process_gift returns a GiftReplyResult with reply and sentiment."""
    result = await mock_pipeline.process_gift(
        user_id="viewer1",
        gift_context='Viewer viewer1 vừa tặng 5x Rose (5 diamonds, ~$0.03)',
    )

    assert isinstance(result, GiftReplyResult)
    assert result.reply == "Cảm ơn bạn đã tặng quà!"
    assert result.sentiment == "positive"


@pytest.mark.asyncio
async def test_process_gift_calls_generate_reply_fn(mock_pipeline):
    """process_gift calls generate_reply_fn with gift system prompt."""
    await mock_pipeline.process_gift(
        user_id="viewer1",
        gift_context='Viewer viewer1 vừa tặng 1x Lion (500 diamonds, ~$2.50)',
    )

    mock_pipeline.generate_reply_fn.assert_called_once()
    call_kwargs = mock_pipeline.generate_reply_fn.call_args
    # system prompt should contain gift thank instruction
    system = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system") or call_kwargs[0][0]
    assert "cảm ơn" in system.lower() or "gift" in system.lower()
    # context should be empty (no RAG chunks for gifts)
    context = call_kwargs.kwargs.get("context") or call_kwargs[1].get("context") or call_kwargs[0][1]
    assert context == ""


@pytest.mark.asyncio
async def test_process_gift_does_not_call_embed_or_retrieve(mock_pipeline):
    """process_gift skips embedding and retrieval (no RAG for gifts)."""
    await mock_pipeline.process_gift(
        user_id="viewer1",
        gift_context='Viewer viewer1 vừa tặng 1x Rose (1 diamonds, ~$0.01)',
    )

    mock_pipeline.embed_fn.assert_not_called()
    mock_pipeline.retrieve_fn.assert_not_called()


@pytest.mark.asyncio
async def test_process_gift_does_not_update_cooldown(mock_pipeline):
    """process_gift does not affect per-user cooldown."""
    await mock_pipeline.process_gift(
        user_id="viewer1",
        gift_context='Viewer viewer1 vừa tặng 1x Rose (1 diamonds, ~$0.01)',
    )

    # User should not be in cooldown map
    assert "viewer1" not in mock_pipeline._filter._last_reply


@pytest.mark.asyncio
async def test_process_gift_uses_seller_tone(mock_pipeline):
    """process_gift injects seller tone into system prompt."""
    mock_pipeline.seller_settings["tone"] = "chuyên nghiệp"

    await mock_pipeline.process_gift(
        user_id="viewer1",
        gift_context='test gift',
    )

    call_kwargs = mock_pipeline.generate_reply_fn.call_args
    system = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system") or call_kwargs[0][0]
    assert "chuyên nghiệp" in system
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_gift_pipeline.py -v` from `backend/`
Expected: FAIL with `ImportError: cannot import name 'GiftReplyResult' from 'app.core.rag.pipeline'`

- [ ] **Step 3: Add GiftReplyResult and process_gift to pipeline.py**

In `backend/app/core/rag/pipeline.py`, add the `GiftReplyResult` dataclass after `RAGResult` (after line 53):

```python
@dataclass
class GiftReplyResult:
    """Result from gift thank-you generation."""
    reply: str
    sentiment: str
```

Add the gift system prompt template after `SYSTEM_PROMPT_TEMPLATE` (after line 29):

```python
GIFT_PROMPT_TEMPLATE = """\
Bạn là AI assistant hỗ trợ bán hàng trên TikTok Live. Một viewer vừa tặng gift cho bạn.

Quy tắc:
- Luôn trả lời bằng tiếng Việt
- Ngắn gọn, chân thành (1-2 câu)
- Cảm ơn viewer đã tặng gift, có thể nhắc tên gift
- Tone: {tone}

Trả lời dưới dạng JSON với đúng 3 field:
- "intent": luôn là "gift_thank"
- "sentiment": cảm xúc tổng thể ("positive" | "neutral" | "negative")
- "reply": nội dung cảm ơn"""
```

Add the `process_gift` method to `RAGPipeline` class (after the `process` method, after line 131):

```python
    async def process_gift(self, user_id: str, gift_context: str) -> GiftReplyResult:
        """Generate a thank-you reply for a gift event.

        Skips embedding, retrieval, and cooldown — gifts always get a response.
        """
        system = GIFT_PROMPT_TEMPLATE.format(
            tone=self.seller_settings.get("tone", "friendly"),
        )

        llm_result: LLMResult = await self.generate_reply_fn(
            system=system,
            context="",
            user_msg=gift_context,
        )

        logger.info(
            "Gift reply for %s (sentiment=%s): %s",
            user_id,
            llm_result.sentiment,
            llm_result.reply[:60],
        )
        return GiftReplyResult(
            reply=llm_result.reply,
            sentiment=llm_result.sentiment,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_gift_pipeline.py -v` from `backend/`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/rag/pipeline.py backend/tests/test_gift_pipeline.py
git commit -m "feat: add process_gift() to RAGPipeline with gift-specific prompt"
```

---

### Task 4: LiveListener GiftEvent Handler

**Files:**
- Modify: `backend/app/core/tiktok/listener.py`
- Test: `backend/tests/test_gift_listener.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_gift_listener.py`:

```python
"""Tests for LiveListener GiftEvent handling and streak filtering."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.tiktok.listener import LiveListener


def _make_mock_client():
    """Create a mock TikTokLiveClient that captures event registrations."""
    client = MagicMock()
    client._events = {}

    def on_decorator(event_class):
        def decorator(fn):
            client._events[event_class.__name__] = fn
            return fn
        return decorator

    client.on = on_decorator
    return client


def _make_gift_event(unique_id, gift_name, diamond_count, repeat_count, streakable, streaking):
    """Create a mock GiftEvent."""
    event = MagicMock()
    event.user.unique_id = unique_id
    event.gift.name = gift_name
    event.gift.diamond_count = diamond_count
    event.gift.streakable = streakable
    event.repeat_count = repeat_count
    event.repeat_end = not streaking if streakable else True
    event.streaking = streaking
    event.value = None if streaking else repeat_count * diamond_count * 0.005
    return event


@pytest.mark.asyncio
async def test_gift_handler_called_for_non_streakable():
    """Non-streakable gifts are dispatched immediately."""
    client = _make_mock_client()

    with patch("app.core.tiktok.listener.GiftEvent"):
        listener = LiveListener(client)

    handler = AsyncMock()
    listener.on_gift(handler)

    event = _make_gift_event("viewer1", "Lion", 500, 1, streakable=False, streaking=False)
    await listener._handle_gift_event(event)

    handler.assert_called_once_with("viewer1", "Lion", 500, 1)


@pytest.mark.asyncio
async def test_gift_handler_called_when_streak_ends():
    """Streakable gifts dispatch only when streak ends (streaking=False)."""
    client = _make_mock_client()

    with patch("app.core.tiktok.listener.GiftEvent"):
        listener = LiveListener(client)

    handler = AsyncMock()
    listener.on_gift(handler)

    event = _make_gift_event("viewer2", "Rose", 1, 10, streakable=True, streaking=False)
    await listener._handle_gift_event(event)

    handler.assert_called_once_with("viewer2", "Rose", 1, 10)


@pytest.mark.asyncio
async def test_gift_handler_skipped_during_streak():
    """Streakable gifts are skipped while streak is ongoing."""
    client = _make_mock_client()

    with patch("app.core.tiktok.listener.GiftEvent"):
        listener = LiveListener(client)

    handler = AsyncMock()
    listener.on_gift(handler)

    event = _make_gift_event("viewer3", "Rose", 1, 3, streakable=True, streaking=True)
    await listener._handle_gift_event(event)

    handler.assert_not_called()


@pytest.mark.asyncio
async def test_on_gift_registers_handler():
    """on_gift() registers a handler in the gift handlers list."""
    client = _make_mock_client()

    with patch("app.core.tiktok.listener.GiftEvent"):
        listener = LiveListener(client)

    handler = AsyncMock()
    listener.on_gift(handler)

    assert handler in listener._gift_handlers
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_gift_listener.py -v` from `backend/`
Expected: FAIL with `ImportError` or `AttributeError` (no `on_gift`, `_handle_gift_event`, `_gift_handlers`)

- [ ] **Step 3: Update LiveListener with GiftEvent support**

Replace `backend/app/core/tiktok/listener.py` with:

```python
import inspect
import logging
from enum import Enum
from typing import Callable

from TikTokLive.client.client import TikTokLiveClient
from TikTokLive.events.custom_events import DisconnectEvent, LiveEndEvent
from TikTokLive.events.proto_events import CommentEvent, GiftEvent

logger = logging.getLogger(__name__)

CommentHandler = Callable[[str, str], None]   # (user_unique_id, comment_text)
GiftHandler = Callable[[str, str, int, int], None]  # (user_unique_id, gift_name, diamond_count, repeat_count)
DisconnectHandler = Callable[[], None]


class ListenerEvent(str, Enum):
    COMMENT = "comment"
    GIFT = "gift"
    DISCONNECT = "disconnect"


class LiveListener:
    """
    Wraps TikTokLiveClient and exposes a simple callback interface.
    The TikTokLive library is NEVER modified — only used via its public API.
    """

    def __init__(self, client: TikTokLiveClient) -> None:
        self._client = client
        self._comment_handlers: list[CommentHandler] = []
        self._gift_handlers: list[GiftHandler] = []
        self._disconnect_handlers: list[DisconnectHandler] = []
        self._register_events()

    def _register_events(self) -> None:
        @self._client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            await self._handle_comment_event(event)

        @self._client.on(GiftEvent)
        async def on_gift(event: GiftEvent):
            await self._handle_gift_event(event)

        @self._client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent):
            await self._handle_disconnect_event(event)

        @self._client.on(LiveEndEvent)
        async def on_live_end(event: LiveEndEvent):
            logger.info("LiveEndEvent received — treating as disconnect")
            await self._handle_disconnect_event(event)

    async def _handle_comment_event(self, event) -> None:
        # Use user_info (not deprecated .user property)
        user = event.user_info.unique_id if event.user_info else "unknown"
        text = event.comment or ""
        logger.debug("Comment from %s: %s", user, text[:80])
        for handler in self._comment_handlers:
            try:
                result = handler(user, text)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Comment handler error")

    async def _handle_gift_event(self, event) -> None:
        """Handle incoming gift events with streak filtering.

        Only dispatches when:
        - Gift is not streakable (single gift), OR
        - Gift is streakable and streak has ended (streaking=False / repeat_end=True)
        """
        # Skip mid-streak events
        if event.gift.streakable and event.streaking:
            logger.debug("Skipping mid-streak gift from %s", event.user.unique_id)
            return

        user = event.user.unique_id
        gift_name = event.gift.name
        diamond_count = event.gift.diamond_count
        repeat_count = event.repeat_count

        logger.info(
            "Gift from %s: %dx %s (%d diamonds each)",
            user, repeat_count, gift_name, diamond_count,
        )

        for handler in self._gift_handlers:
            try:
                result = handler(user, gift_name, diamond_count, repeat_count)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Gift handler error")

    async def _handle_disconnect_event(self, event) -> None:
        logger.info("Disconnect event received")
        for handler in self._disconnect_handlers:
            try:
                result = handler()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Disconnect handler error")

    def on_comment(self, handler: CommentHandler) -> None:
        self._comment_handlers.append(handler)

    def on_gift(self, handler: GiftHandler) -> None:
        self._gift_handlers.append(handler)

    def on_disconnect(self, handler: DisconnectHandler) -> None:
        self._disconnect_handlers.append(handler)

    async def start(self) -> None:
        """Non-blocking: start connection in background."""
        await self._client.start()

    async def stop(self) -> None:
        await self._client.disconnect()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_gift_listener.py -v` from `backend/`
Expected: 4 tests PASS

- [ ] **Step 5: Run full test suite to check no regressions**

Run: `python3 -m pytest tests/ -v` from `backend/`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/tiktok/listener.py backend/tests/test_gift_listener.py
git commit -m "feat: add GiftEvent handler to LiveListener with streak filtering"
```

---

### Task 5: _handle_gift Wiring in Sessions API

**Files:**
- Modify: `backend/app/api/v1/sessions.py`
- Test: `backend/tests/test_gift_wiring.py` (new)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_gift_wiring.py`:

```python
"""Tests for _handle_gift session wiring — DB save, broadcast, LLM reply, TikTok send."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.core.ai.base import LLMResult
from app.core.rag.pipeline import RAGPipeline, GiftReplyResult
from app.core.session_state import get_session_state
from app.models.session import LiveSession


@pytest.fixture
async def active_session(db_session, test_seller):
    """Create an active session and configure session state."""
    session = LiveSession(seller_id=test_seller.id, status="active")
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    state = get_session_state(test_seller.id)
    state.active_session_id = session.id
    state.active_replier = AsyncMock()
    state.active_pipeline = MagicMock(spec=RAGPipeline)
    state.active_pipeline.process_gift = AsyncMock(
        return_value=GiftReplyResult(reply="Cảm ơn bạn!", sentiment="positive")
    )
    state.active_pipeline.seller_settings = {"auto_reply_enabled": True}
    state.bot_paused = False

    return session, state


@pytest.mark.asyncio
async def test_handle_gift_saves_gift_log(db_session, test_seller, active_session):
    """_handle_gift saves a GiftLog record to the database."""
    session, state = active_session

    with patch("app.api.v1.sessions.get_session_factory") as mock_factory, \
         patch("app.api.v1.sessions.broadcast", new_callable=AsyncMock) as mock_broadcast:
        # Make get_session_factory return a factory that yields our test db_session
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=db_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session_ctx)

        from app.api.v1.sessions import _handle_gift
        await _handle_gift(test_seller.id, "viewer1", "Rose", 1, 5)

    # Verify gift was saved
    from sqlalchemy import select
    from app.models.gift import GiftLog
    result = await db_session.execute(select(GiftLog).where(GiftLog.session_id == session.id))
    gifts = result.scalars().all()
    assert len(gifts) == 1
    assert gifts[0].gift_name == "Rose"
    assert gifts[0].diamond_count == 1
    assert gifts[0].repeat_count == 5
    assert gifts[0].total_diamonds == 5
    assert gifts[0].estimated_usd == pytest.approx(0.025)
    assert gifts[0].thank_reply == "Cảm ơn bạn!"


@pytest.mark.asyncio
async def test_handle_gift_broadcasts_gift_and_reply(db_session, test_seller, active_session):
    """_handle_gift broadcasts both 'gift' and 'gift_reply' WebSocket messages."""
    session, state = active_session

    broadcast_calls = []

    with patch("app.api.v1.sessions.get_session_factory") as mock_factory, \
         patch("app.api.v1.sessions.broadcast", new_callable=AsyncMock) as mock_broadcast:
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=db_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session_ctx)

        from app.api.v1.sessions import _handle_gift
        await _handle_gift(test_seller.id, "viewer1", "Lion", 500, 1)

        # Check broadcast calls
        assert mock_broadcast.call_count >= 2
        call_types = [c.args[0]["type"] for c in mock_broadcast.call_args_list]
        assert "gift" in call_types
        assert "gift_reply" in call_types


@pytest.mark.asyncio
async def test_handle_gift_skipped_when_bot_paused(db_session, test_seller, active_session):
    """_handle_gift still logs gift but skips LLM reply when bot is paused."""
    session, state = active_session
    state.bot_paused = True

    with patch("app.api.v1.sessions.get_session_factory") as mock_factory, \
         patch("app.api.v1.sessions.broadcast", new_callable=AsyncMock) as mock_broadcast:
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=db_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session_ctx)

        from app.api.v1.sessions import _handle_gift
        await _handle_gift(test_seller.id, "viewer1", "Rose", 1, 3)

    # Gift should still be saved
    from sqlalchemy import select
    from app.models.gift import GiftLog
    result = await db_session.execute(select(GiftLog).where(GiftLog.session_id == session.id))
    gifts = result.scalars().all()
    assert len(gifts) == 1
    # But no thank reply (LLM not called)
    assert gifts[0].thank_reply is None
    # Pipeline should not be called
    state.active_pipeline.process_gift.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_gift_wiring.py -v` from `backend/`
Expected: FAIL with `ImportError: cannot import name '_handle_gift'`

- [ ] **Step 3: Add _handle_gift to sessions.py**

In `backend/app/api/v1/sessions.py`, add the import for `GiftLog`:

```python
from app.models.gift import GiftLog
```

Add the `_handle_gift` function after `_handle_comment` (after line 148):

```python
async def _handle_gift(
    seller_id: str, user: str, gift_name: str, diamond_count: int, repeat_count: int
) -> None:
    """Background callback: save gift → broadcast → LLM thank → reply → broadcast."""
    state = get_session_state(seller_id)

    if state.active_session_id is None or state.active_pipeline is None:
        return

    total_diamonds = diamond_count * repeat_count
    estimated_usd = total_diamonds * 0.005

    # 1. Save GiftLog to DB
    gift_log_id: str | None = None
    async with get_session_factory()() as db:
        gift = GiftLog(
            session_id=state.active_session_id,
            user_unique_id=user,
            gift_name=gift_name,
            diamond_count=diamond_count,
            repeat_count=repeat_count,
            total_diamonds=total_diamonds,
            estimated_usd=estimated_usd,
        )
        db.add(gift)
        await db.commit()
        await db.refresh(gift)
        gift_log_id = gift.id

    # 2. Broadcast gift event to dashboard
    await broadcast(
        {
            "type": "gift",
            "seller_id": seller_id,
            "gift_log_id": gift_log_id,
            "user": user,
            "gift_name": gift_name,
            "diamond_count": diamond_count,
            "repeat_count": repeat_count,
            "total_diamonds": total_diamonds,
            "estimated_usd": estimated_usd,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    # 3. Generate LLM thank-you (skip if bot paused or auto_reply disabled)
    auto_reply = state.active_pipeline.seller_settings.get("auto_reply_enabled", True)
    if state.bot_paused or not auto_reply:
        return

    gift_context = (
        f"Viewer {user} vừa tặng {repeat_count}x {gift_name} "
        f"({total_diamonds} diamonds, ~${estimated_usd:.2f})"
    )

    try:
        result = await state.active_pipeline.process_gift(user, gift_context)
    except Exception:
        logger.exception("Failed to generate gift thank-you for %s", user)
        return

    # 4. Send reply via TikTok
    try:
        if state.active_replier is not None:
            await state.active_replier.send(result.reply)
    except Exception:
        logger.exception("Failed to send gift thank-you to TikTok")

    # 5. Update GiftLog with thank_reply
    async with get_session_factory()() as db:
        gift = await db.get(GiftLog, gift_log_id)
        if gift:
            gift.thank_reply = result.reply
            await db.commit()

    # 6. Broadcast gift reply to dashboard
    await broadcast(
        {
            "type": "gift_reply",
            "seller_id": seller_id,
            "gift_log_id": gift_log_id,
            "content": result.reply,
            "user": user,
        }
    )
```

- [ ] **Step 4: Register gift handler in start_session**

In `backend/app/api/v1/sessions.py`, in the `start_session` function, add after line 211 (`listener.on_disconnect(...)`):

```python
    listener.on_gift(functools.partial(_handle_gift, seller_id))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_gift_wiring.py -v` from `backend/`
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/sessions.py backend/tests/test_gift_wiring.py
git commit -m "feat: add _handle_gift wiring with DB save, broadcast, LLM reply"
```

---

### Task 6: Session Gifts API Endpoint

**Files:**
- Modify: `backend/app/api/v1/sessions.py`
- Test: `backend/tests/test_gift_api.py` (new)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_gift_api.py`:

```python
"""Tests for gift-related API endpoints."""
import pytest
from app.models.session import LiveSession
from app.models.gift import GiftLog


@pytest.mark.asyncio
async def test_get_session_gifts(auth_client, db_session, test_seller):
    """GET /api/v1/sessions/{id}/gifts returns gift logs for a session."""
    session = LiveSession(seller_id=test_seller.id, status="ended")
    db_session.add(session)
    await db_session.commit()

    gift1 = GiftLog(
        session_id=session.id,
        user_unique_id="viewer1",
        gift_name="Rose",
        diamond_count=1,
        repeat_count=5,
        total_diamonds=5,
        estimated_usd=0.025,
        thank_reply="Cảm ơn bạn!",
    )
    gift2 = GiftLog(
        session_id=session.id,
        user_unique_id="viewer2",
        gift_name="Lion",
        diamond_count=500,
        repeat_count=1,
        total_diamonds=500,
        estimated_usd=2.5,
    )
    db_session.add_all([gift1, gift2])
    await db_session.commit()

    resp = await auth_client.get(f"/api/v1/sessions/{session.id}/gifts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["gift_name"] in ("Rose", "Lion")


@pytest.mark.asyncio
async def test_get_session_gifts_empty(auth_client, db_session, test_seller):
    """GET /api/v1/sessions/{id}/gifts returns empty list when no gifts."""
    session = LiveSession(seller_id=test_seller.id, status="ended")
    db_session.add(session)
    await db_session.commit()

    resp = await auth_client.get(f"/api/v1/sessions/{session.id}/gifts")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_session_gifts_not_found(auth_client):
    """GET /api/v1/sessions/{id}/gifts returns 404 for unknown session."""
    resp = await auth_client.get("/api/v1/sessions/nonexistent/gifts")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_session_gifts_forbidden(auth_client, db_session):
    """GET /api/v1/sessions/{id}/gifts returns 403 for another seller's session."""
    from app.models.seller import Seller
    from app.core.security import hash_password
    from app.core.crypto import encrypt

    other_seller = Seller(
        id="other-seller-999",
        name="Other Shop",
        username="othershop",
        password_hash=hash_password("pass"),
        tiktok_unique_id="@other",
        tiktok_session_id_encrypted=encrypt("s"),
        tiktok_target_idc_encrypted=encrypt("t"),
    )
    db_session.add(other_seller)
    await db_session.commit()

    session = LiveSession(seller_id="other-seller-999", status="ended")
    db_session.add(session)
    await db_session.commit()

    resp = await auth_client.get(f"/api/v1/sessions/{session.id}/gifts")
    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_gift_api.py -v` from `backend/`
Expected: FAIL with 404 (endpoint doesn't exist yet)

- [ ] **Step 3: Add session gifts endpoint**

In `backend/app/api/v1/sessions.py`, add the import for `GiftLogResponse`:

```python
from app.schemas.gift import GiftLogResponse
```

Add the endpoint after the existing `get_session_messages` endpoint (after line 343):

```python
@router.get("/{session_id}/gifts", response_model=list[GiftLogResponse])
async def get_session_gifts(
    session_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
) -> list[GiftLogResponse]:
    session = await db.get(LiveSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.seller_id != current_seller.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this session")

    offset = (page - 1) * limit
    result = await db.execute(
        select(GiftLog)
        .where(GiftLog.session_id == session_id)
        .order_by(GiftLog.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return [GiftLogResponse.model_validate(g) for g in result.scalars().all()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_gift_api.py -v` from `backend/`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/sessions.py backend/tests/test_gift_api.py
git commit -m "feat: add GET /sessions/{id}/gifts endpoint with auth and pagination"
```

---

### Task 7: Gift Analytics Queries

**Files:**
- Modify: `backend/app/api/v1/analytics.py`
- Test: `backend/tests/test_gift_analytics.py` (new)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_gift_analytics.py`:

```python
"""Tests for gift analytics in GET /api/v1/analytics/."""
import pytest
from app.models.session import LiveSession
from app.models.gift import GiftLog


@pytest.mark.asyncio
async def test_analytics_includes_gift_stats(auth_client, db_session, test_seller):
    """Analytics response includes gift_stats with correct aggregations."""
    session = LiveSession(seller_id=test_seller.id, status="ended")
    db_session.add(session)
    await db_session.commit()

    gifts = [
        GiftLog(
            session_id=session.id, user_unique_id="viewer1",
            gift_name="Rose", diamond_count=1, repeat_count=10,
            total_diamonds=10, estimated_usd=0.05,
        ),
        GiftLog(
            session_id=session.id, user_unique_id="viewer1",
            gift_name="Lion", diamond_count=500, repeat_count=1,
            total_diamonds=500, estimated_usd=2.5,
        ),
        GiftLog(
            session_id=session.id, user_unique_id="viewer2",
            gift_name="Rose", diamond_count=1, repeat_count=5,
            total_diamonds=5, estimated_usd=0.025,
        ),
    ]
    db_session.add_all(gifts)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()

    gs = data["gift_stats"]
    assert gs["total_gifts"] == 3
    assert gs["total_diamonds"] == 515
    assert gs["estimated_usd"] == pytest.approx(2.575)

    # Top gifters: viewer1 has 510, viewer2 has 5
    assert len(gs["top_gifters"]) == 2
    assert gs["top_gifters"][0]["user"] == "viewer1"
    assert gs["top_gifters"][0]["total_diamonds"] == 510
    assert gs["top_gifters"][0]["gift_count"] == 2

    # Gift breakdown: Rose=15 diamonds (2 gifts), Lion=500 diamonds (1 gift)
    breakdown = {g["gift_name"]: g for g in gs["gift_breakdown"]}
    assert breakdown["Rose"]["count"] == 2
    assert breakdown["Rose"]["total_diamonds"] == 15
    assert breakdown["Lion"]["count"] == 1
    assert breakdown["Lion"]["total_diamonds"] == 500


@pytest.mark.asyncio
async def test_analytics_gift_stats_empty(auth_client, db_session, test_seller):
    """Analytics returns zeroed gift_stats when no gifts exist."""
    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()

    gs = data["gift_stats"]
    assert gs["total_gifts"] == 0
    assert gs["total_diamonds"] == 0
    assert gs["estimated_usd"] == 0.0
    assert gs["top_gifters"] == []
    assert gs["gift_breakdown"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_gift_analytics.py -v` from `backend/`
Expected: FAIL (either `gift_stats` key missing or wrong values)

- [ ] **Step 3: Add gift stats query to analytics endpoint**

In `backend/app/api/v1/analytics.py`, add imports:

```python
from app.models.gift import GiftLog
from app.schemas.gift import GiftStats, TopGifter, GiftBreakdown
```

After the `unanswered_count` query (after line 89), add the gift stats queries:

```python
    # Gift stats
    gift_session_subquery = select(LiveSession.id).where(session_filter).scalar_subquery()

    total_gifts = (
        await db.scalar(
            select(func.count(GiftLog.id)).where(
                GiftLog.session_id.in_(gift_session_subquery)
            )
        )
        or 0
    )

    total_diamonds = (
        await db.scalar(
            select(func.coalesce(func.sum(GiftLog.total_diamonds), 0)).where(
                GiftLog.session_id.in_(gift_session_subquery)
            )
        )
        or 0
    )

    total_gift_usd = (
        await db.scalar(
            select(func.coalesce(func.sum(GiftLog.estimated_usd), 0.0)).where(
                GiftLog.session_id.in_(gift_session_subquery)
            )
        )
        or 0.0
    )

    # Top gifters (top 5 by total diamonds)
    top_gifter_rows = await db.execute(
        select(
            GiftLog.user_unique_id,
            func.sum(GiftLog.total_diamonds).label("sum_diamonds"),
            func.count(GiftLog.id).label("gift_count"),
        )
        .where(GiftLog.session_id.in_(gift_session_subquery))
        .group_by(GiftLog.user_unique_id)
        .order_by(func.sum(GiftLog.total_diamonds).desc())
        .limit(5)
    )
    top_gifters = [
        TopGifter(user=row[0], total_diamonds=int(row[1]), gift_count=int(row[2]))
        for row in top_gifter_rows.all()
    ]

    # Gift breakdown by gift type
    gift_breakdown_rows = await db.execute(
        select(
            GiftLog.gift_name,
            func.count(GiftLog.id).label("count"),
            func.sum(GiftLog.total_diamonds).label("sum_diamonds"),
        )
        .where(GiftLog.session_id.in_(gift_session_subquery))
        .group_by(GiftLog.gift_name)
        .order_by(func.sum(GiftLog.total_diamonds).desc())
    )
    gift_breakdown = [
        GiftBreakdown(gift_name=row[0], count=int(row[1]), total_diamonds=int(row[2]))
        for row in gift_breakdown_rows.all()
    ]

    gift_stats = GiftStats(
        total_gifts=total_gifts,
        total_diamonds=int(total_diamonds),
        estimated_usd=float(total_gift_usd),
        top_gifters=top_gifters,
        gift_breakdown=gift_breakdown,
    )
```

Update the return statement to include `gift_stats`:

```python
    return AnalyticsResponse(
        total_sessions=total_sessions,
        total_comments=total_comments,
        total_replies=total_replies,
        reply_rate=reply_rate,
        intent_breakdown=intent_breakdown,
        sentiment_breakdown=sentiment_breakdown,
        unanswered_count=unanswered_count,
        gift_stats=gift_stats,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_gift_analytics.py -v` from `backend/`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/analytics.py backend/tests/test_gift_analytics.py
git commit -m "feat: add gift_stats (total, top gifters, breakdown) to analytics endpoint"
```

---

### Task 8: Full Backend Test Suite Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full backend test suite**

Run: `python3 -m pytest tests/ -v` from `backend/`
Expected: All tests pass (previous 93 + new ~18 gift tests)

- [ ] **Step 2: Fix any failures**

If any tests fail, read the failing test and source file, fix the issue, re-run.

- [ ] **Step 3: Commit any fixes**

```bash
git add -A && git commit -m "fix: resolve test failures from gift tracking integration"
```

(Skip this step if no fixes were needed.)

---

### Task 9: Frontend Types and API Client

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/ws.ts`

- [ ] **Step 1: Add gift types to api.ts**

In `frontend/lib/api.ts`, add after `TestReplyResult` interface (after line 86):

```typescript
// Gift tracking
export interface GiftLogEntry {
  id: string;
  session_id: string;
  user_unique_id: string;
  gift_name: string;
  diamond_count: number;
  repeat_count: number;
  total_diamonds: number;
  estimated_usd: number;
  thank_reply: string | null;
  created_at: string;
}

export interface TopGifter {
  user: string;
  total_diamonds: number;
  gift_count: number;
}

export interface GiftBreakdown {
  gift_name: string;
  count: number;
  total_diamonds: number;
}

export interface GiftStats {
  total_gifts: number;
  total_diamonds: number;
  estimated_usd: number;
  top_gifters: TopGifter[];
  gift_breakdown: GiftBreakdown[];
}
```

- [ ] **Step 2: Add gift_stats to AnalyticsData**

In `frontend/lib/api.ts`, update `AnalyticsData` interface:

```typescript
export interface AnalyticsData {
  total_sessions: number;
  total_comments: number;
  total_replies: number;
  reply_rate: number;
  intent_breakdown: Record<string, number>;
  unanswered_count: number;
  gift_stats: GiftStats | null;
}
```

- [ ] **Step 3: Add api.sessions.gifts() method**

In `frontend/lib/api.ts`, inside `api.sessions`, add after the `messages` method (after line 256):

```typescript
    gifts(sessionId: string, params: { page?: number; limit?: number } = {}): Promise<GiftLogEntry[]> {
      const { page = 1, limit = 50 } = params;
      return request(
        `/api/v1/sessions/${sessionId}/gifts${qs({ page, limit })}`,
        { method: "GET" },
      );
    },
```

- [ ] **Step 4: Add gift and gift_reply to WSMessage union in ws.ts**

In `frontend/lib/ws.ts`, add to the `WSMessage` union type (after the `"reply"` entry, around line 11):

```typescript
  | {
      type: "gift";
      gift_log_id: string;
      user: string;
      gift_name: string;
      diamond_count: number;
      repeat_count: number;
      total_diamonds: number;
      estimated_usd: number;
      timestamp: string;
    }
  | { type: "gift_reply"; gift_log_id: string; content: string; user: string }
  | { type: "alert"; severity: string; message_id: string; comment: string; user: string }
```

- [ ] **Step 5: Verify build passes**

Run: `npm run build` from `frontend/`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/ws.ts
git commit -m "feat: add gift types, API method, and WebSocket message types to frontend"
```

---

### Task 10: GiftFeed Component

**Files:**
- Create: `frontend/components/monitor/GiftFeed.tsx`
- Modify: `frontend/app/monitor/page.tsx`

- [ ] **Step 1: Create GiftFeed component**

Create `frontend/components/monitor/GiftFeed.tsx`:

```tsx
"use client";
import { useEffect, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Gift } from "lucide-react";
import type { WSMessage } from "@/lib/ws";

export type GiftFeedItem = Extract<WSMessage, { type: "gift" }> & {
  reply?: string;
};

interface Props {
  items: GiftFeedItem[];
}

export function GiftFeed({ items }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [items.length]);

  return (
    <div className="flex flex-col gap-2 h-[480px] overflow-y-auto rounded-md border bg-amber-50 p-3">
      {items.length === 0 && (
        <p className="m-auto text-sm text-muted-foreground">
          Waiting for gifts…
        </p>
      )}
      {items.map((item) => (
        <div
          key={item.gift_log_id}
          className="rounded-md bg-white border border-amber-200 p-3 text-sm shadow-sm"
        >
          <div className="flex items-center justify-between gap-2 mb-1">
            <div className="flex items-center gap-1.5">
              <Gift className="h-4 w-4 text-amber-500" />
              <span className="font-semibold text-slate-800">{item.user}</span>
            </div>
            <div className="flex items-center gap-1">
              <Badge variant="outline" className="text-xs bg-amber-50 text-amber-700 border-amber-300">
                {item.gift_name}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {new Date(item.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
          <p className="text-slate-700">
            {item.repeat_count}x {item.gift_name}
            <span className="ml-2 text-xs text-muted-foreground">
              ({item.total_diamonds} diamonds, ~${item.estimated_usd.toFixed(2)})
            </span>
          </p>
          {item.reply && (
            <p className="mt-2 pl-3 border-l-2 border-amber-400 text-slate-600 text-xs italic">
              Bot: {item.reply}
            </p>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 2: Update Monitor page with 2-column layout and gift handlers**

Replace `frontend/app/monitor/page.tsx` with:

```tsx
"use client";
import { useState, useCallback } from "react";
import { toast } from "sonner";
import { SessionControl } from "@/components/monitor/SessionControl";
import { CommentFeed, type FeedItem } from "@/components/monitor/CommentFeed";
import { GiftFeed, type GiftFeedItem } from "@/components/monitor/GiftFeed";
import { BotControls } from "@/components/monitor/BotControls";
import { useSession } from "@/hooks/useSession";
import { useWebSocket } from "@/hooks/useWebSocket";

const MAX_FEED_ITEMS = 200;

export default function MonitorPage() {
  const { state, loading, start, stop, refresh } = useSession();
  const [feedItems, setFeedItems] = useState<FeedItem[]>([]);
  const [giftItems, setGiftItems] = useState<GiftFeedItem[]>([]);
  const [paused, setPaused] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const addOrUpdate = useCallback((updater: (items: FeedItem[]) => FeedItem[]) => {
    setFeedItems(updater);
  }, []);

  useWebSocket({
    comment: (msg) => {
      addOrUpdate((items) => {
        const updated = [...items, { ...msg }];
        if (updated.length > MAX_FEED_ITEMS) {
          const trimmed = updated.slice(-MAX_FEED_ITEMS);
          const removedIds = new Set(
            updated.slice(0, updated.length - MAX_FEED_ITEMS).map((i) => i.message_id)
          );
          if (selectedId && removedIds.has(selectedId)) {
            setSelectedId(null);
          }
          return trimmed;
        }
        return updated;
      });
    },
    reply: (msg) => {
      addOrUpdate((items) =>
        items.map((item) =>
          item.message_id === msg.message_id
            ? { ...item, reply: msg.content, intent: msg.intent }
            : item,
        ),
      );
    },
    gift: (msg) => {
      setGiftItems((items) => {
        const updated = [...items, { ...msg }];
        return updated.length > MAX_FEED_ITEMS
          ? updated.slice(-MAX_FEED_ITEMS)
          : updated;
      });
    },
    gift_reply: (msg) => {
      setGiftItems((items) =>
        items.map((item) =>
          item.gift_log_id === msg.gift_log_id
            ? { ...item, reply: msg.content }
            : item,
        ),
      );
    },
    status: (msg) => {
      if (typeof msg.connected === "boolean") {
        refresh();
      }
      if (typeof msg.paused === "boolean") {
        setPaused(msg.paused);
      }
    },
    error: (msg) => {
      toast.error(msg.message);
    },
  });

  async function handleStart() {
    try {
      await start();
      toast.success("Session started");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to start session");
    }
  }

  async function handleStop() {
    try {
      await stop();
      setFeedItems([]);
      setGiftItems([]);
      toast.success("Session stopped");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to stop session");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Live Monitor</h2>
        <SessionControl
          state={state}
          loading={loading}
          onStart={handleStart}
          onStop={handleStop}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1fr_260px]">
        <CommentFeed
          items={feedItems}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />

        <GiftFeed items={giftItems} />

        <div className="space-y-4 rounded-md border p-4">
          <h3 className="font-semibold text-sm">Bot Controls</h3>
          <BotControls
            paused={paused}
            connected={state.connected}
            replyTargetId={selectedId}
          />
          {state.session && (
            <div className="text-xs text-muted-foreground space-y-1 border-t pt-3">
              <p>Session ID: <span className="font-mono">{state.session.id.slice(0, 8)}…</span></p>
              <p>Started: {new Date(state.session.started_at).toLocaleTimeString()}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify build passes**

Run: `npm run build` from `frontend/`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/components/monitor/GiftFeed.tsx frontend/app/monitor/page.tsx
git commit -m "feat: add GiftFeed component and 2-column monitor layout"
```

---

### Task 11: Gift Analytics Frontend Components

**Files:**
- Create: `frontend/components/analytics/GiftStats.tsx`
- Modify: `frontend/app/analytics/page.tsx`

- [ ] **Step 1: Create GiftStats component**

Create `frontend/components/analytics/GiftStats.tsx`:

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GiftStats as GiftStatsType } from "@/lib/api";
import { Diamond, DollarSign } from "lucide-react";

interface Props {
  stats: GiftStatsType;
}

export function GiftStatsSection({ stats }: Props) {
  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Tổng gifts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{stats.total_gifts}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-1 text-sm font-medium text-muted-foreground">
              <Diamond className="h-4 w-4" /> Tổng diamonds
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{stats.total_diamonds.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-1 text-sm font-medium text-muted-foreground">
              <DollarSign className="h-4 w-4" /> Doanh thu ước tính
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">${stats.estimated_usd.toFixed(2)}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Top Gifters */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Gifters</CardTitle>
          </CardHeader>
          <CardContent>
            {stats.top_gifters.length === 0 ? (
              <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
            ) : (
              <div className="space-y-2">
                {stats.top_gifters.map((gifter, i) => (
                  <div key={gifter.user} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-muted-foreground w-5">{i + 1}.</span>
                      <span className="font-medium">{gifter.user}</span>
                    </div>
                    <div className="flex items-center gap-3 text-muted-foreground">
                      <span>{gifter.gift_count} gifts</span>
                      <span className="font-semibold text-foreground">
                        {gifter.total_diamonds.toLocaleString()} <Diamond className="inline h-3 w-3" />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Gift Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Loại gift</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {stats.gift_breakdown.length === 0 ? (
              <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
            ) : (
              stats.gift_breakdown.map((g) => {
                const max = stats.gift_breakdown[0]?.total_diamonds ?? 1;
                return (
                  <div key={g.gift_name} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>{g.gift_name} ({g.count}x)</span>
                      <span className="font-medium">{g.total_diamonds.toLocaleString()} <Diamond className="inline h-3 w-3" /></span>
                    </div>
                    <div className="h-2 rounded-full bg-amber-100">
                      <div
                        className="h-2 rounded-full bg-amber-500 transition-all"
                        style={{ width: `${Math.round((g.total_diamonds / max) * 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Update Analytics page to render GiftStats**

In `frontend/app/analytics/page.tsx`, add the import:

```tsx
import { GiftStatsSection } from "@/components/analytics/GiftStats";
```

Add the GiftStats section after the existing grid (after the `UnansweredSummary` section, inside the `{data && (...)}` block):

```tsx
          {data.gift_stats && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Gift & Revenue</h3>
              <GiftStatsSection stats={data.gift_stats} />
            </div>
          )}
```

- [ ] **Step 3: Verify build passes**

Run: `npm run build` from `frontend/`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/components/analytics/GiftStats.tsx frontend/app/analytics/page.tsx
git commit -m "feat: add gift analytics components (stats cards, top gifters, breakdown)"
```

---

### Task 12: Full Build Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full backend test suite**

Run: `python3 -m pytest tests/ -v` from `backend/`
Expected: All tests pass

- [ ] **Step 2: Run frontend build**

Run: `npm run build` from `frontend/`
Expected: Build succeeds with no errors

- [ ] **Step 3: Fix any failures and commit**

If anything fails, fix and commit:

```bash
git add -A && git commit -m "fix: resolve build issues from gift tracking integration"
```

(Skip this step if no fixes needed.)
