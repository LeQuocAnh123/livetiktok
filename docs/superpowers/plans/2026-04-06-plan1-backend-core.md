# Backend Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng backend core hoàn chỉnh: FastAPI app, database models, TikTok listener (đọc comment), replier (gửi comment) với throttle và encryption — tất cả test được mà không cần frontend.

**Architecture:** FastAPI app import TikTokLive lib trực tiếp từ thư mục cha (`pip install -e ../`). Business logic nằm trong `core/` hoàn toàn độc lập với FastAPI. SQLite + SQLAlchemy + Alembic cho DB. Fernet encryption cho TikTok credentials.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, pydantic-settings, cryptography (Fernet), pytest-asyncio, httpx (test client)

**Spec:** `docs/superpowers/specs/2026-04-06-tiktok-live-ai-bot-design.md`

---

## File Map

```
backend/
├── pyproject.toml                        # CREATE — backend dependencies
├── .env.example                          # CREATE — env template
├── alembic.ini                           # CREATE — alembic config
├── alembic/
│   ├── env.py                            # CREATE — alembic env
│   └── versions/                         # CREATE (empty, alembic fills this)
├── app/
│   ├── __init__.py                       # CREATE (empty)
│   ├── main.py                           # CREATE — FastAPI app + lifespan
│   ├── config.py                         # CREATE — pydantic-settings
│   ├── database.py                       # CREATE — SQLAlchemy engine + session
│   ├── models/
│   │   ├── __init__.py                   # CREATE — export all models
│   │   ├── seller.py                     # CREATE — Seller ORM model
│   │   ├── knowledge.py                  # CREATE — KnowledgeChunk ORM model
│   │   ├── session.py                    # CREATE — LiveSession ORM model
│   │   └── message.py                    # CREATE — MessageLog ORM model
│   ├── schemas/
│   │   ├── __init__.py                   # CREATE (empty)
│   │   ├── session.py                    # CREATE — Pydantic request/response
│   │   └── message.py                    # CREATE — MessageLog schema
│   ├── core/
│   │   ├── __init__.py                   # CREATE (empty)
│   │   ├── crypto.py                     # CREATE — Fernet encrypt/decrypt
│   │   └── tiktok/
│   │       ├── __init__.py               # CREATE (empty)
│   │       ├── listener.py               # CREATE — wrap TikTokLiveClient
│   │       └── replier.py                # CREATE — send_room_chat + throttle
│   └── api/
│       ├── __init__.py                   # CREATE (empty)
│       ├── v1/
│       │   ├── __init__.py               # CREATE (empty)
│       │   └── sessions.py               # CREATE — start/stop/status routes
│       └── ws.py                         # CREATE — WebSocket /ws/monitor
└── tests/
    ├── __init__.py                       # CREATE (empty)
    ├── conftest.py                       # CREATE — pytest fixtures
    ├── test_crypto.py                    # CREATE
    ├── test_replier.py                   # CREATE
    ├── test_listener.py                  # CREATE
    └── test_sessions_api.py              # CREATE
```

---

## Task 1: Backend Project Setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`

- [ ] **Step 1.1: Tạo `backend/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "livetiktok-backend"
version = "0.1.0"
requires-python = ">=3.10"
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
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "httpx>=0.26.0",
    "ruff>=0.4.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
```

- [ ] **Step 1.2: Cài dependencies**

```bash
cd /home/quocanh/live-tiktok/livetiktok
python3 -m venv .venv
source .venv/bin/activate
pip install -e .                     # cài TikTokLive lib từ thư mục gốc
pip install -e backend/[dev]         # cài backend + dev deps
```

Expected: Không có lỗi. Verify: `python -c "from TikTokLive import TikTokLiveClient; print('OK')`

- [ ] **Step 1.3: Tạo `backend/.env.example`**

```bash
# Security — generate bằng: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SECRET_KEY=

# AI Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
AI_REPLY_PROVIDER=claude
AI_EMBED_PROVIDER=openai

# TikTok
TIKTOK_SESSION_ID=
TIKTOK_TARGET_IDC=useast1a
TIKTOK_SIGN_API_KEY=
WHITELIST_AUTHENTICATED_SESSION_ID_HOST=tiktok.eulerstream.com

# App
DATABASE_URL=sqlite+aiosqlite:///./app.db
CHROMA_PATH=./chroma_data
REPLY_DELAY_MIN=5
REPLY_DELAY_MAX=15
```

- [ ] **Step 1.4: Tạo `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Security
    secret_key: str

    # AI
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ai_reply_provider: str = "claude"
    ai_embed_provider: str = "openai"

    # TikTok
    tiktok_session_id: str = ""
    tiktok_target_idc: str = "useast1a"
    tiktok_sign_api_key: str = ""
    whitelist_authenticated_session_id_host: str = "tiktok.eulerstream.com"

    # App
    database_url: str = "sqlite+aiosqlite:///./app.db"
    chroma_path: str = "./chroma_data"
    reply_delay_min: int = 5
    reply_delay_max: int = 15


settings = Settings()
```

- [ ] **Step 1.5: Copy .env và verify config load**

```bash
cd backend
cp .env.example .env
# Edit .env: điền SECRET_KEY (chạy lệnh generate ở .env.example)
python -c "from app.config import settings; print(settings.reply_delay_min)"
```

Expected output: `5`

- [ ] **Step 1.6: Commit**

```bash
git add backend/
git commit -m "feat: backend project setup — pyproject, config, env"
```

---

## Task 2: Database Setup (SQLAlchemy + Alembic)

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/seller.py`
- Create: `backend/app/models/knowledge.py`
- Create: `backend/app/models/session.py`
- Create: `backend/app/models/message.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`

- [ ] **Step 2.1: Tạo `backend/app/database.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2.2: Tạo `backend/app/models/seller.py`**

```python
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    tiktok_unique_id: Mapped[str] = mapped_column(String, nullable=False)
    # Stored encrypted via Fernet — NEVER store plaintext
    tiktok_session_id_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    tiktok_target_idc_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    bot_settings: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {
            "tone": "friendly",
            "blacklist_keywords": [],
            "reply_delay_min": 5,
            "reply_delay_max": 15,
            "user_cooldown_seconds": 60,
            "max_replies_per_session": 500,
            "auto_reply_enabled": True,
        },
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sessions: Mapped[list["LiveSession"]] = relationship(back_populates="seller")
    knowledge_chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="seller")
```

- [ ] **Step 2.3: Tạo `backend/app/models/knowledge.py`**

```python
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class KnowledgeCategory(str, Enum):
    PRODUCT = "product"
    POLICY = "policy"
    FAQ = "faq"


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id: Mapped[str] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, default=KnowledgeCategory.FAQ)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    needs_reembed: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    seller: Mapped["Seller"] = relationship(back_populates="knowledge_chunks")
```

- [ ] **Step 2.4: Tạo `backend/app/models/session.py`**

```python
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"
    PAUSED = "paused"


class LiveSession(Base):
    __tablename__ = "live_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id: Mapped[str] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    tiktok_room_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=SessionStatus.ACTIVE)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    seller: Mapped["Seller"] = relationship(back_populates="sessions")
    messages: Mapped[list["MessageLog"]] = relationship(back_populates="session")
```

- [ ] **Step 2.5: Tạo `backend/app/models/message.py`**

```python
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MessageLog(Base):
    __tablename__ = "message_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("live_sessions.id"), nullable=False)
    user_unique_id: Mapped[str] = mapped_column(String, nullable=False)
    comment: Mapped[str] = mapped_column(String, nullable=False)
    reply: Mapped[str | None] = mapped_column(String, nullable=True)
    intent: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    chunks_used: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["LiveSession"] = relationship(back_populates="messages")
```

- [ ] **Step 2.6: Tạo `backend/app/models/__init__.py`**

```python
from app.models.seller import Seller
from app.models.knowledge import KnowledgeChunk, KnowledgeCategory
from app.models.session import LiveSession, SessionStatus
from app.models.message import MessageLog

__all__ = [
    "Seller",
    "KnowledgeChunk",
    "KnowledgeCategory",
    "LiveSession",
    "SessionStatus",
    "MessageLog",
]
```

- [ ] **Step 2.7: Setup Alembic**

> **Lưu ý:** `backend/.env` phải có `SECRET_KEY` hợp lệ trước khi chạy bất kỳ lệnh Alembic nào,
> vì `app/config.py` được import khi Alembic khởi động.

```bash
cd backend
alembic init alembic
```

Sau đó sửa `backend/alembic/env.py` — thay toàn bộ nội dung:

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.config import settings
from app.database import Base
import app.models  # noqa: F401 — trigger all model imports

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 2.8: Tạo và chạy migration đầu tiên**

```bash
cd backend
alembic revision --autogenerate -m "init tables"
alembic upgrade head
```

Expected: File migration tạo trong `alembic/versions/`. DB file `app.db` tạo với 4 tables.

Verify: `python -c "import sqlite3; c=sqlite3.connect('app.db'); print(c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall())"`

Expected: `[('sellers',), ('knowledge_chunks',), ('live_sessions',), ('message_logs',)]`

- [ ] **Step 2.9: Commit**

```bash
git add backend/
git commit -m "feat: database models + alembic setup — 4 tables"
```

---

## Task 3: Crypto Module (Fernet Encryption)

**Files:**
- Create: `backend/app/core/crypto.py`
- Create: `backend/tests/test_crypto.py`

- [ ] **Step 3.1: Viết test trước (TDD)**

Tạo `backend/tests/test_crypto.py`:

```python
import pytest
from app.core.crypto import encrypt, decrypt


def test_encrypt_returns_string():
    result = encrypt("my-secret")
    assert isinstance(result, str)
    assert result != "my-secret"


def test_decrypt_returns_original():
    original = "session-id-abc123"
    encrypted = encrypt(original)
    assert decrypt(encrypted) == original


def test_different_encryptions_for_same_input():
    # Fernet is nondeterministic
    enc1 = encrypt("same")
    enc2 = encrypt("same")
    assert enc1 != enc2


def test_decrypt_invalid_raises():
    with pytest.raises(Exception):
        decrypt("not-valid-fernet-token")
```

- [ ] **Step 3.2: Chạy test — expect FAIL**

```bash
cd backend
python -m pytest tests/test_crypto.py -v
```

Expected: `ImportError: cannot import name 'encrypt'`

- [ ] **Step 3.3: Implement `backend/app/core/crypto.py`**

```python
from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    return Fernet(settings.secret_key.encode())


def encrypt(plaintext: str) -> str:
    """Encrypt a string using Fernet symmetric encryption."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string. Raises InvalidToken if tampered."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
```

- [ ] **Step 3.4: Chạy test — expect PASS**

```bash
python -m pytest tests/test_crypto.py -v
```

Expected: `4 passed`

- [ ] **Step 3.5: Commit**

```bash
git add backend/app/core/crypto.py backend/tests/test_crypto.py
git commit -m "feat: fernet encryption for TikTok credentials"
```

---

## Task 4: TikTok Replier (send_room_chat + Throttle)

**Files:**
- Create: `backend/app/core/tiktok/replier.py`
- Create: `backend/tests/test_replier.py`

- [ ] **Step 4.1: Viết test trước**

Tạo `backend/tests/test_replier.py`:

```python
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.tiktok.replier import Replier


@pytest.fixture
def mock_web_client():
    client = MagicMock()
    client.send_room_chat = AsyncMock(return_value={"status": "ok"})
    return client


async def test_send_applies_throttle(mock_web_client):
    replier = Replier(
        web_client=mock_web_client,
        delay_min=0.1,
        delay_max=0.2,
    )
    start = time.monotonic()
    await replier.send("hello")
    elapsed = time.monotonic() - start
    assert elapsed >= 0.1
    mock_web_client.send_room_chat.assert_called_once()


async def test_send_calls_with_correct_args(mock_web_client):
    # Credentials are set via web_client.set_session() before calling send()
    # Replier only passes content — session cookies already set on the web client
    replier = Replier(web_client=mock_web_client, delay_min=0, delay_max=0)
    await replier.send("test reply")
    mock_web_client.send_room_chat.assert_called_once_with(content="test reply")


async def test_send_propagates_web_client_errors(mock_web_client):
    mock_web_client.send_room_chat = AsyncMock(side_effect=ValueError("Room ID required"))
    replier = Replier(web_client=mock_web_client, delay_min=0, delay_max=0)
    with pytest.raises(ValueError, match="Room ID"):
        await replier.send("hi")
```

- [ ] **Step 4.2: Chạy test — expect FAIL**

```bash
python -m pytest tests/test_replier.py -v
```

Expected: `ImportError: cannot import name 'Replier'`

- [ ] **Step 4.3: Implement `backend/app/core/tiktok/replier.py`**

> **Lưu ý API:** `Replier` nhận `web_client` là instance của `TikTokWebClient` (truy cập qua `tiktok_client.web`).
> Credentials được set trước qua `web_client.set_session(session_id, tt_target_idc)` — sau đó
> `send_room_chat(content=content)` tự đọc từ cookies. Không cần truyền session_id lại mỗi lần gửi.

```python
import asyncio
import logging
import random
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Replier:
    """
    Wraps TikTokWebClient.send_room_chat with random throttle delay.

    Usage:
        replier = Replier(web_client=tiktok_client.web, delay_min=5, delay_max=15)
        # Credentials phải được set trước khi gọi send():
        tiktok_client.web.set_session(session_id, tt_target_idc)
        await replier.send("Hello!")
    """

    web_client: object          # TikTokWebClient — accessed via tiktok_client.web
    delay_min: float = 5.0
    delay_max: float = 15.0

    async def send(self, content: str) -> dict:
        """Send a chat message with throttle delay. Raises on failure."""
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.debug("Throttle: waiting %.1fs before reply", delay)
        await asyncio.sleep(delay)

        # session_id + tt_target_idc đã được set vào cookies qua web_client.set_session()
        result = await self.web_client.send_room_chat(content=content)
        logger.info("Reply sent: %s", content[:50])
        return result
```

- [ ] **Step 4.4: Chạy test — expect PASS**

```bash
python -m pytest tests/test_replier.py -v
```

Expected: `3 passed`

- [ ] **Step 4.5: Commit**

```bash
git add backend/app/core/tiktok/ backend/tests/test_replier.py
git commit -m "feat: TikTok replier with throttle — wraps send_room_chat"
```

---

## Task 5: TikTok Listener (wrap TikTokLiveClient)

**Files:**
- Create: `backend/app/core/tiktok/listener.py`
- Create: `backend/tests/test_listener.py`

- [ ] **Step 5.1: Viết test trước**

Tạo `backend/tests/test_listener.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from app.core.tiktok.listener import LiveListener, ListenerEvent


@pytest.fixture
def mock_tiktok_client():
    client = MagicMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.is_live = AsyncMock(return_value=True)
    client.on = MagicMock(side_effect=lambda event_type: lambda fn: fn)
    return client


def test_listener_event_enum():
    assert ListenerEvent.COMMENT == "comment"
    assert ListenerEvent.DISCONNECT == "disconnect"


async def test_on_comment_calls_handler(mock_tiktok_client):
    received = []

    listener = LiveListener(client=mock_tiktok_client)
    listener.on_comment(lambda user, text: received.append((user, text)))

    # Simulate firing the comment handler directly
    await listener._handle_comment_event(
        MagicMock(user_info=MagicMock(unique_id="user1"), comment="hello")
    )
    assert received == [("user1", "hello")]


async def test_on_disconnect_updates_status(mock_tiktok_client):
    disconnected = []
    listener = LiveListener(client=mock_tiktok_client)
    listener.on_disconnect(lambda: disconnected.append(True))

    await listener._handle_disconnect_event(MagicMock())
    assert disconnected == [True]
```

- [ ] **Step 5.2: Chạy test — expect FAIL**

```bash
python -m pytest tests/test_listener.py -v
```

Expected: `ImportError: cannot import name 'LiveListener'`

- [ ] **Step 5.3: Implement `backend/app/core/tiktok/listener.py`**

```python
import logging
from enum import Enum
from typing import Callable, Awaitable

from TikTokLive.client.client import TikTokLiveClient
from TikTokLive.events.custom_events import ConnectEvent, DisconnectEvent, LiveEndEvent
from TikTokLive.events.proto_events import CommentEvent

logger = logging.getLogger(__name__)


class ListenerEvent(str, Enum):
    COMMENT = "comment"
    CONNECT = "connect"
    DISCONNECT = "disconnect"


CommentHandler = Callable[[str, str], None]     # (user_unique_id, comment_text)
DisconnectHandler = Callable[[], None]


class LiveListener:
    """
    Wraps TikTokLiveClient and exposes a simple callback interface.
    The TikTokLive library is NEVER modified — only used via its public API.
    """

    def __init__(self, client: TikTokLiveClient) -> None:
        self._client = client
        self._comment_handlers: list[CommentHandler] = []
        self._disconnect_handlers: list[DisconnectHandler] = []
        self._register_events()

    def _register_events(self) -> None:
        @self._client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            await self._handle_comment_event(event)

        @self._client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent):
            await self._handle_disconnect_event(event)

        @self._client.on(LiveEndEvent)
        async def on_live_end(event: LiveEndEvent):
            logger.info("LiveEndEvent received — treating as disconnect")
            await self._handle_disconnect_event(event)

    async def _handle_comment_event(self, event) -> None:
        # Use user_info (not deprecated user property)
        user = event.user_info.unique_id if event.user_info else "unknown"
        text = event.comment or ""
        logger.debug("Comment from %s: %s", user, text[:80])
        for handler in self._comment_handlers:
            try:
                handler(user, text)
            except Exception:
                logger.exception("Comment handler error")

    async def _handle_disconnect_event(self, event) -> None:
        logger.info("Disconnect event received")
        for handler in self._disconnect_handlers:
            try:
                handler()
            except Exception:
                logger.exception("Disconnect handler error")

    def on_comment(self, handler: CommentHandler) -> None:
        self._comment_handlers.append(handler)

    def on_disconnect(self, handler: DisconnectHandler) -> None:
        self._disconnect_handlers.append(handler)

    async def start(self) -> None:
        """Non-blocking: starts connection in background task."""
        await self._client.start()

    async def stop(self) -> None:
        await self._client.disconnect()
```

- [ ] **Step 5.4: Chạy test — expect PASS**

```bash
python -m pytest tests/test_listener.py -v
```

Expected: `3 passed`

- [ ] **Step 5.5: Commit**

```bash
git add backend/app/core/tiktok/listener.py backend/tests/test_listener.py
git commit -m "feat: TikTok listener — wraps TikTokLiveClient events"
```

---

## Task 6: FastAPI App + Health Endpoint

**Files:**
- Create: `backend/app/main.py`

- [ ] **Step 6.1: Tạo `backend/app/main.py`**

```python
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set TikTok env var bắt buộc cho send_room_chat
os.environ.setdefault(
    "WHITELIST_AUTHENTICATED_SESSION_ID_HOST",
    settings.whitelist_authenticated_session_id_host,
)


async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up — creating DB tables if needed")
    await create_tables()
    logger.info("Database ready")
    yield
    # Shutdown
    logger.info("Shutting down")


app = FastAPI(title="TikTok Live AI Bot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ai_reply_provider": settings.ai_reply_provider,
        "ai_embed_provider": settings.ai_embed_provider,
    }
```

- [ ] **Step 6.2: Chạy server thử**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Mở browser hoặc curl: `curl http://localhost:8000/health`

Expected:
```json
{"status":"ok","ai_reply_provider":"claude","ai_embed_provider":"openai"}
```

- [ ] **Step 6.3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: FastAPI app + health endpoint + DB lifespan"
```

---

## Task 7: Sessions API (start/stop/status)

**Files:**
- Create: `backend/app/schemas/session.py`
- Create: `backend/app/api/v1/sessions.py`
- Modify: `backend/app/main.py` — include router
- Create: `backend/tests/test_sessions_api.py`

- [ ] **Step 7.1: Tạo `backend/app/schemas/session.py`**

```python
from datetime import datetime
from app.models.session import SessionStatus
from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    seller_id: str
    tiktok_unique_id: str


class SessionResponse(BaseModel):
    id: str
    seller_id: str
    tiktok_room_id: int | None = None
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None = None

    model_config = {"from_attributes": True}


class SessionStatusResponse(BaseModel):
    connected: bool
    session: SessionResponse | None = None
```

- [ ] **Step 7.2: Viết test trước**

Tạo `backend/tests/conftest.py`:

```python
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.database import Base, get_db

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    # Patch create_tables so lifespan doesn't touch production DB
    with patch("app.main.create_tables", new_callable=AsyncMock):
        from app.main import app
        app.dependency_overrides[get_db] = override_get_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
        app.dependency_overrides.clear()
```

Tạo `backend/tests/test_sessions_api.py`:

```python
import pytest


async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_get_status_no_session(client):
    response = await client.get("/api/v1/sessions/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
    assert data["session"] is None
```

- [ ] **Step 7.3: Chạy test — expect FAIL**

```bash
python -m pytest tests/test_sessions_api.py -v
```

Expected: Fail vì `/api/v1/sessions/status` chưa tồn tại.

- [ ] **Step 7.4: Tạo `backend/app/api/v1/sessions.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.session import LiveSession, SessionStatus
from app.schemas.session import SessionStatusResponse

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

# In-memory state: chỉ 1 session active tại 1 thời điểm (single-seller v1)
_active_session_id: str | None = None


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

    return SessionStatusResponse(connected=True, session=session)
```

- [ ] **Step 7.5: Register router trong `backend/app/main.py`**

Thêm vào cuối `main.py` (trước hoặc sau health endpoint):

```python
from app.api.v1.sessions import router as sessions_router
app.include_router(sessions_router)
```

- [ ] **Step 7.6: Chạy test — expect PASS**

```bash
python -m pytest tests/test_sessions_api.py -v
```

Expected: `2 passed`

- [ ] **Step 7.7: Chạy toàn bộ test suite**

```bash
python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

Expected: Tất cả pass, coverage > 60% (sẽ tăng khi thêm test ở Plan 2).

- [ ] **Step 7.8: Commit**

```bash
git add backend/app/schemas/ backend/app/api/ backend/tests/ backend/app/main.py
git commit -m "feat: sessions API + test client fixtures"
```

---

## Task 8: WebSocket Monitor Endpoint

**Files:**
- Create: `backend/app/api/ws.py`
- Modify: `backend/app/main.py` — include WS router

- [ ] **Step 8.1: Tạo `backend/app/schemas/message.py`**

```python
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class MessageLogSchema(BaseModel):
    id: str
    session_id: str
    user_unique_id: str
    comment: str
    reply: str | None = None
    intent: str
    chunks_used: list[Any] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class WSMessage(BaseModel):
    """WebSocket message envelope."""
    type: str           # comment | reply | status | error
    payload: dict[str, Any]
```

- [ ] **Step 8.2: Tạo `backend/app/api/ws.py`**

```python
import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

# Simple broadcast registry — single-seller v1
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
            # Wait for client commands (pause/resume/manual_reply)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from WS client, ignoring")
                continue
            logger.info("WS command received: %s", msg.get("type"))
            # Command handling will be wired in Plan 2 (RAG pipeline)
    except WebSocketDisconnect:
        if websocket in _connections:
            _connections.remove(websocket)
        logger.info("Dashboard client disconnected (%d remaining)", len(_connections))
    except Exception:
        logger.exception("WebSocket error")
        if websocket in _connections:
            _connections.remove(websocket)
```

- [ ] **Step 8.3: Register WS router trong `main.py`**

```python
from app.api.ws import router as ws_router
app.include_router(ws_router)
```

- [ ] **Step 8.4: Test WebSocket thủ công**

```bash
uvicorn app.main:app --reload --port 8000
```

Trong terminal khác:
```bash
pip install websockets
python -c "
import asyncio, websockets, json

async def test():
    async with websockets.connect('ws://localhost:8000/ws/monitor') as ws:
        print('Connected!')
        await ws.send(json.dumps({'type': 'ping'}))
        await asyncio.sleep(1)

asyncio.run(test())
"
```

Expected: `Connected!` — không crash.

- [ ] **Step 8.5: Commit**

```bash
git add backend/app/api/ws.py backend/app/schemas/message.py backend/app/main.py
git commit -m "feat: WebSocket /ws/monitor endpoint + broadcast utility"
```

---

## Task 9: Makefile + .gitignore

**Files:**
- Create: `Makefile` (root level)
- Modify: `.gitignore`

- [ ] **Step 9.1: Tạo `Makefile` ở root**

```makefile
.PHONY: install install-fe setup dev-backend dev-frontend test lint db-migrate db-reset

# Setup
install:
	pip install -e .
	pip install -e backend/[dev]

install-fe:
	cd frontend && npm install

setup: install
	cp -n backend/.env.example backend/.env || true
	@echo "✅ Setup done. Edit backend/.env before running."

# Development
dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# Database
db-migrate:
	cd backend && alembic upgrade head

db-reset:
	cd backend && alembic downgrade base && alembic upgrade head

# Testing
test:
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	cd backend && ruff check app/ tests/

# Production
up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build
```

- [ ] **Step 9.2: Cập nhật `.gitignore` ở root**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
dist/
build/

# Environment
.env
backend/.env
frontend/.env.local

# Database
backend/app.db
backend/*.db

# ChromaDB
backend/chroma_data/

# Node
frontend/node_modules/
frontend/.next/

# IDE
.vscode/
.idea/
*.swp
```

- [ ] **Step 9.3: Final test run**

```bash
make test
```

Expected: Tất cả tests pass.

- [ ] **Step 9.4: Commit cuối Plan 1**

```bash
git add Makefile .gitignore
git commit -m "chore: Makefile + gitignore — backend core complete"
```

---

## Verification Checklist

Sau khi hoàn thành Plan 1, verify các điều sau:

- [ ] `make install` chạy không lỗi
- [ ] `from TikTokLive import TikTokLiveClient` import được trong `backend/`
- [ ] `make test` → tất cả pass, coverage ≥ 60%
- [ ] `make dev-backend` → server chạy tại port 8000
- [ ] `curl http://localhost:8000/health` → `{"status":"ok",...}`
- [ ] `curl http://localhost:8000/api/v1/sessions/status` → `{"connected":false,...}`
- [ ] WebSocket `/ws/monitor` accept connection không crash
- [ ] `alembic upgrade head` tạo 4 tables trong SQLite
- [ ] `make lint` → exit code 0, không có lỗi ruff
- [ ] `pip install aiosqlite` KHÔNG cần thiết riêng lẻ (đã có trong pyproject.toml)

---

## Next: Plan 2 — RAG Pipeline

Plan 2 sẽ build:
- `core/ai/` — Claude + OpenAI providers
- `core/rag/` — ChromaDB + embedder + pipeline
- `api/v1/knowledge.py` — CRUD + bulk import
- `api/v1/settings.py` — bot config
- Wiring listener → filter → RAG → replier → broadcast WS
