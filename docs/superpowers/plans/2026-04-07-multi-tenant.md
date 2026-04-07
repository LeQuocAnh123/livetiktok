# Multi-Tenant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert single-tenant TikTok Live Bot to multi-tenant, allowing multiple sellers with isolated data and sessions.

**Architecture:** Add auth fields to Seller model, authenticate sellers via username/password, extract seller_id from JWT in all API endpoints, isolate session state and WebSocket connections per seller.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, bcrypt/passlib, JWT, Next.js

---

## File Structure

### Backend - New Files
- `backend/alembic/versions/xxxx_add_seller_auth_fields.py` - Migration
- `backend/scripts/manage_seller.py` - CLI tool for seller management

### Backend - Modified Files
- `backend/app/models/seller.py` - Add username, password_hash, is_active
- `backend/app/core/security.py` - Add password hashing, update JWT to use seller_id
- `backend/app/core/session_state.py` - Multi-tenant state dict
- `backend/app/schemas/auth.py` - Add SellerResponse schema
- `backend/app/schemas/session.py` - Remove seller_id from SessionStartRequest
- `backend/app/schemas/settings.py` - Remove seller_id from TestReplyRequest
- `backend/app/api/v1/auth.py` - Seller-based authentication
- `backend/app/api/v1/knowledge.py` - Use get_current_seller
- `backend/app/api/v1/settings.py` - Use get_current_seller
- `backend/app/api/v1/analytics.py` - Use get_current_seller
- `backend/app/api/v1/sessions.py` - Use get_current_seller, pass seller_id to callbacks
- `backend/app/api/ws.py` - Isolated connections per seller
- `backend/tests/conftest.py` - Update fixtures for multi-tenant

### Frontend - Modified Files
- `frontend/lib/api.ts` - Remove SELLER_ID, update types
- `frontend/.env.example` - Remove NEXT_PUBLIC_SELLER_ID
- `frontend/components/nav/Sidebar.tsx` - Show seller name
- `docker-compose.yml` - Remove NEXT_PUBLIC_SELLER_ID

---

## Task 1: Add Auth Fields to Seller Model

**Files:**
- Modify: `backend/app/models/seller.py`
- Test: `backend/tests/test_seller_model.py` (new)

- [ ] **Step 1: Write failing test for new Seller fields**

Create `backend/tests/test_seller_model.py`:

```python
"""Tests for Seller model auth fields."""
import pytest
from app.models.seller import Seller


def test_seller_has_auth_fields():
    """Seller model should have username, password_hash, is_active fields."""
    seller = Seller(
        name="Test Shop",
        username="testshop",
        password_hash="hashed_password",
        tiktok_unique_id="@testshop",
        tiktok_session_id_encrypted="enc_session",
        tiktok_target_idc_encrypted="enc_idc",
    )
    assert seller.username == "testshop"
    assert seller.password_hash == "hashed_password"
    assert seller.is_active is True  # default


def test_seller_is_active_defaults_true():
    """is_active should default to True."""
    seller = Seller(
        name="Test Shop",
        username="testshop",
        password_hash="hashed",
        tiktok_unique_id="@testshop",
        tiktok_session_id_encrypted="enc",
        tiktok_target_idc_encrypted="enc",
    )
    assert seller.is_active is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_seller_model.py -v`
Expected: FAIL - `username` field not defined

- [ ] **Step 3: Add auth fields to Seller model**

Edit `backend/app/models/seller.py`:

```python
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.knowledge import KnowledgeChunk
    from app.models.session import LiveSession


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
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

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_seller_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/seller.py backend/tests/test_seller_model.py
git commit -m "feat: add username, password_hash, is_active fields to Seller model"
```

---

## Task 2: Create Alembic Migration

**Files:**
- Create: `backend/alembic/versions/xxxx_add_seller_auth_fields.py`

- [ ] **Step 1: Generate migration**

Run: `cd backend && alembic revision --autogenerate -m "add_seller_auth_fields"`

- [ ] **Step 2: Review and edit migration file**

The generated file should look like:

```python
"""add_seller_auth_fields

Revision ID: <generated>
Revises: 5b83f14952d2
Create Date: <generated>
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '<generated>'
down_revision: Union[str, None] = '5b83f14952d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sellers', sa.Column('username', sa.String(), nullable=True))
    op.add_column('sellers', sa.Column('password_hash', sa.String(), nullable=True))
    op.add_column('sellers', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.create_unique_constraint('uq_sellers_username', 'sellers', ['username'])


def downgrade() -> None:
    op.drop_constraint('uq_sellers_username', 'sellers', type_='unique')
    op.drop_column('sellers', 'is_active')
    op.drop_column('sellers', 'password_hash')
    op.drop_column('sellers', 'username')
```

Note: `username` and `password_hash` are nullable initially so existing rows don't break. After running CLI to set them, a later migration can make them NOT NULL.

- [ ] **Step 3: Run migration**

Run: `cd backend && alembic upgrade head`
Expected: Migration applied successfully

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "migration: add seller auth fields (username, password_hash, is_active)"
```

---

## Task 3: Add Password Hashing to Security Module

**Files:**
- Modify: `backend/app/core/security.py`
- Test: `backend/tests/test_security.py` (new)

- [ ] **Step 1: Write failing test for password hashing**

Create `backend/tests/test_security.py`:

```python
"""Tests for security module."""
import pytest
from app.core.security import hash_password, verify_seller_password


def test_hash_password_returns_hash():
    """hash_password should return a bcrypt hash string."""
    password = "mysecretpassword"
    hashed = hash_password(password)
    assert hashed != password
    assert hashed.startswith("$2b$")  # bcrypt prefix


def test_verify_seller_password_correct():
    """verify_seller_password returns True for correct password."""
    password = "mysecretpassword"
    hashed = hash_password(password)
    assert verify_seller_password(password, hashed) is True


def test_verify_seller_password_incorrect():
    """verify_seller_password returns False for incorrect password."""
    hashed = hash_password("correctpassword")
    assert verify_seller_password("wrongpassword", hashed) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_security.py -v`
Expected: FAIL - `hash_password` not defined

- [ ] **Step 3: Add password hashing functions**

Edit `backend/app/core/security.py`:

```python
"""Security utilities for JWT and password verification."""

from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import get_settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_seller_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(seller_id: str) -> str:
    """Create a JWT access token for the given seller_id."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"sub": seller_id, "type": "seller", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    """
    Decode and verify a JWT token.
    Returns the payload dict if valid, None otherwise.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        return None


def verify_password(plain_password: str, username: str) -> bool:
    """
    DEPRECATED: Legacy admin password verification.
    Kept for backward compatibility during migration.
    """
    settings = get_settings()
    return username == settings.admin_username and plain_password == settings.admin_password
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_security.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/security.py backend/tests/test_security.py
git commit -m "feat: add bcrypt password hashing functions"
```

---

## Task 4: Update Auth Schemas

**Files:**
- Modify: `backend/app/schemas/auth.py`

- [ ] **Step 1: Update schemas with SellerResponse**

Edit `backend/app/schemas/auth.py`:

```python
"""Auth request/response schemas."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login credentials."""

    username: str
    password: str


class SellerResponse(BaseModel):
    """Current seller info returned after login."""

    id: str
    username: str
    name: str
    tiktok_unique_id: str

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    """DEPRECATED: Use SellerResponse instead."""

    username: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/auth.py
git commit -m "feat: add SellerResponse schema for multi-tenant auth"
```

---

## Task 5: Implement Seller-Based Authentication

**Files:**
- Modify: `backend/app/api/v1/auth.py`
- Test: `backend/tests/test_auth_api.py` (new)

- [ ] **Step 1: Write failing test for seller login**

Create `backend/tests/test_auth_api.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_auth_api.py -v`
Expected: FAIL - login doesn't authenticate sellers yet

- [ ] **Step 3: Implement seller-based auth**

Edit `backend/app/api/v1/auth.py`:

```python
"""Authentication API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import create_access_token, decode_access_token, verify_seller_password
from app.database import get_db
from app.models.seller import Seller
from app.schemas.auth import LoginRequest, MessageResponse, SellerResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_auth_cookie(response: Response, token: str) -> None:
    """Set the auth cookie with appropriate settings."""
    settings = get_settings()
    max_age = settings.jwt_expire_hours * 3600
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=max_age,
    )


def _clear_auth_cookie(response: Response) -> None:
    """Clear the auth cookie."""
    response.delete_cookie(key="access_token")


@router.post("/login", response_model=SellerResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate seller and set httpOnly cookie."""
    # Find seller by username
    result = await db.execute(
        select(Seller).where(Seller.username == body.username)
    )
    seller = result.scalar_one_or_none()

    if seller is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not seller.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")

    if not verify_seller_password(body.password, seller.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(seller.id)
    _set_auth_cookie(response, token)
    logger.info("Seller logged in: %s (id=%s)", seller.username, seller.id)

    return SellerResponse(
        id=seller.id,
        username=seller.username,
        name=seller.name,
        tiktok_unique_id=seller.tiktok_unique_id,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    """Clear auth cookie."""
    _clear_auth_cookie(response)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=SellerResponse)
async def get_current_user_info(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated seller info."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    seller_id = payload.get("sub")
    seller = await db.get(Seller, seller_id)
    if not seller or not seller.is_active:
        raise HTTPException(status_code=401, detail="Account not found or disabled")

    return SellerResponse(
        id=seller.id,
        username=seller.username,
        name=seller.name,
        tiktok_unique_id=seller.tiktok_unique_id,
    )


async def get_current_seller(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Seller:
    """
    Dependency to get the current authenticated seller.
    Use with Depends(get_current_seller) on protected routes.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    seller_id = payload.get("sub")
    seller = await db.get(Seller, seller_id)
    if not seller or not seller.is_active:
        raise HTTPException(status_code=401, detail="Account not found or disabled")

    return seller
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_auth_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/auth.py backend/tests/test_auth_api.py
git commit -m "feat: implement seller-based authentication"
```

---

## Task 6: Update Test Fixtures for Multi-Tenant

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Update conftest.py with seller auth fixture**

Edit `backend/tests/conftest.py`:

```python
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.database import Base, get_db
from app.core.security import hash_password

_TEST_SELLER_ID = "test-seller-001"

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
    """Unauthenticated client."""
    async def override_get_db():
        yield db_session

    with patch("app.main.create_tables", new_callable=AsyncMock):
        from app.main import app

        app.dependency_overrides[get_db] = override_get_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
        app.dependency_overrides.clear()


@pytest.fixture
async def test_seller(db_session):
    """Create a test seller with known credentials."""
    from app.models.seller import Seller

    seller = Seller(
        id=_TEST_SELLER_ID,
        name="Test Shop",
        username="testshop",
        password_hash=hash_password("testpass123"),
        tiktok_unique_id="@testshop",
        tiktok_session_id_encrypted="enc_session",
        tiktok_target_idc_encrypted="enc_idc",
    )
    db_session.add(seller)
    await db_session.commit()
    return seller


@pytest.fixture
async def auth_client(db_session, test_seller):
    """Authenticated client with seller auth cookie set."""
    async def override_get_db():
        yield db_session

    with patch("app.main.create_tables", new_callable=AsyncMock):
        from app.main import app
        from app.core.security import create_access_token

        app.dependency_overrides[get_db] = override_get_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            # Create and set auth token cookie for test seller
            token = create_access_token(_TEST_SELLER_ID)
            c.cookies.set("access_token", token)
            yield c
        app.dependency_overrides.clear()


@pytest.fixture
async def seller_id(test_seller) -> str:
    """Return the test seller's ID."""
    return _TEST_SELLER_ID


@pytest.fixture(autouse=True)
def reset_session_state():
    """Reset all session state between tests."""
    from app.core.session_state import session_states

    session_states.clear()
    yield
    session_states.clear()
```

- [ ] **Step 2: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: update fixtures for multi-tenant authentication"
```

---

## Task 7: Update Session State for Multi-Tenant

**Files:**
- Modify: `backend/app/core/session_state.py`

- [ ] **Step 1: Update session_state.py for multi-tenant**

Edit `backend/app/core/session_state.py`:

```python
"""
Shared session state — single source of truth for live session globals.

This module exists to avoid circular imports between ws.py and sessions.py.
Both modules import from here instead of importing each other.
"""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.core.tiktok.listener import LiveListener
    from app.core.tiktok.replier import Replier
    from app.core.rag.pipeline import RAGPipeline


class SessionState:
    """Holds the active session state for a single seller."""

    def __init__(self, seller_id: str) -> None:
        self.seller_id: str = seller_id
        self.active_session_id: Optional[str] = None
        self.active_listener: Optional["LiveListener"] = None
        self.active_replier: Optional["Replier"] = None
        self.active_pipeline: Optional["RAGPipeline"] = None
        self.active_task: Optional[Any] = None  # asyncio.Task
        self.bot_paused: bool = False
        self.reply_count: int = 0

    def reset(self) -> None:
        """Reset all state to initial values (keeps seller_id)."""
        self.active_session_id = None
        self.active_listener = None
        self.active_replier = None
        self.active_pipeline = None
        self.active_task = None
        self.bot_paused = False
        self.reply_count = 0


# Multi-tenant state dict keyed by seller_id
session_states: dict[str, SessionState] = {}


def get_session_state(seller_id: str) -> SessionState:
    """Get or create session state for a seller."""
    if seller_id not in session_states:
        session_states[seller_id] = SessionState(seller_id)
    return session_states[seller_id]


# DEPRECATED: Keep for backward compatibility during migration
session_state = SessionState("legacy")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/session_state.py
git commit -m "feat: convert session_state to multi-tenant dict"
```

---

## Task 8: Update Knowledge API

**Files:**
- Modify: `backend/app/api/v1/knowledge.py`
- Modify: `backend/app/schemas/knowledge.py`

- [ ] **Step 1: Update knowledge schemas to remove seller_id from create**

Edit `backend/app/schemas/knowledge.py` - find `KnowledgeChunkCreate` and remove `seller_id`:

```python
class KnowledgeChunkCreate(BaseModel):
    """Request body for creating a knowledge chunk."""
    content: str
    category: KnowledgeCategory
    metadata: dict[str, Any] = {}
    # seller_id removed - comes from JWT
```

- [ ] **Step 2: Update knowledge API to use get_current_seller**

Edit `backend/app/api/v1/knowledge.py`:

Replace:
```python
from app.api.v1.auth import get_current_user
```

With:
```python
from app.api.v1.auth import get_current_seller
```

Update `create_chunk`:
```python
@router.post("/", response_model=KnowledgeChunkResponse, status_code=201)
async def create_chunk(
    body: KnowledgeChunkCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    chunk = KnowledgeChunk(
        seller_id=seller.id,
        content=body.content,
        category=body.category,
        metadata_=body.metadata,
        needs_reembed=True,
    )
    db.add(chunk)
    await db.commit()
    await db.refresh(chunk)
    background_tasks.add_task(embed_and_store, chunk.id, seller.id)
    return KnowledgeChunkResponse.from_orm_model(chunk)
```

Update `list_chunks` - remove `seller_id` param:
```python
@router.get("/", response_model=KnowledgeListResponse)
async def list_chunks(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    offset = (page - 1) * limit
    count_result = await db.execute(
        select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.seller_id == seller.id)
    )
    total = count_result.scalar() or 0

    items_result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.seller_id == seller.id)
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
```

Update `update_chunk` and `delete_chunk_endpoint` to use seller and verify ownership:
```python
@router.put("/{chunk_id}", response_model=KnowledgeChunkResponse)
async def update_chunk(
    chunk_id: str,
    body: KnowledgeChunkUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    chunk = await db.get(KnowledgeChunk, chunk_id)
    if chunk is None or chunk.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Chunk not found")
    # ... rest unchanged


@router.delete("/{chunk_id}", status_code=204)
async def delete_chunk_endpoint(
    chunk_id: str,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    chunk = await db.get(KnowledgeChunk, chunk_id)
    if chunk is None or chunk.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Chunk not found")
    # ... rest unchanged
```

Update `preview_knowledge`:
```python
@router.post("/preview", response_model=CsvPreviewResponse)
async def preview_knowledge(
    file: UploadFile,
    _: Seller = Depends(get_current_seller),
):
    # ... rest unchanged
```

Update `upload_knowledge` - remove `seller_id` param:
```python
@router.post("/upload", response_model=UploadResponse)
async def upload_knowledge(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    """Bulk import from CSV."""
    filename = file.filename or ""
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content_bytes = await file.read()
    rows = _parse_csv_bytes(content_bytes)

    if len(rows) > MAX_UPLOAD_ROWS:
        raise HTTPException(...)

    if not rows or "content" not in rows[0].keys():
        raise HTTPException(...)

    # No need to call _require_seller - seller already validated by dependency

    created = 0
    skipped = 0
    errors: list[str] = []
    chunks = []

    for i, row in enumerate(rows, start=1):
        # ... same logic but use seller.id instead of seller_id param
        chunk = KnowledgeChunk(
            seller_id=seller.id,
            # ...
        )
        # ...

    await db.commit()
    for chunk in chunks:
        await db.refresh(chunk)
        background_tasks.add_task(embed_and_store, chunk.id, seller.id)

    return UploadResponse(created=created, skipped=skipped, errors=errors)
```

- [ ] **Step 3: Run knowledge tests**

Run: `cd backend && python3 -m pytest tests/test_knowledge_api.py -v`
Expected: PASS (tests use auth_client fixture)

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/knowledge.py backend/app/schemas/knowledge.py
git commit -m "refactor: knowledge API uses seller from JWT instead of params"
```

---

## Task 9: Update Settings API

**Files:**
- Modify: `backend/app/api/v1/settings.py`
- Modify: `backend/app/schemas/settings.py`

- [ ] **Step 1: Update settings schemas**

Edit `backend/app/schemas/settings.py` - remove `seller_id` from `TestReplyRequest`:

```python
class TestReplyRequest(BaseModel):
    comment: str
    # seller_id removed - comes from JWT
```

- [ ] **Step 2: Update settings API**

Edit `backend/app/api/v1/settings.py`:

```python
"""Settings API — get/update bot settings, test-reply preview."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_seller
from app.core.ai.factory import get_embed_provider, get_reply_provider
from app.core.rag import retriever
from app.core.rag.filter import detect_intent
from app.core.rag.pipeline import SYSTEM_PROMPT_TEMPLATE
from app.database import get_db
from app.models.seller import Seller
from app.schemas.settings import (
    BotSettingsResponse,
    BotSettingsUpdate,
    TestReplyRequest,
    TestReplyResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("/", response_model=BotSettingsResponse)
async def get_settings(
    seller: Seller = Depends(get_current_seller),
):
    return BotSettingsResponse(**seller.bot_settings)


@router.put("/", response_model=BotSettingsResponse)
async def update_settings(
    body: BotSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    # Merge: only update fields that were explicitly provided
    updated = dict(seller.bot_settings)
    patch = body.model_dump(exclude_none=True)
    updated.update(patch)
    seller.bot_settings = updated

    await db.commit()
    await db.refresh(seller)
    return BotSettingsResponse(**seller.bot_settings)


@router.post("/test-reply", response_model=TestReplyResponse)
async def test_reply(
    body: TestReplyRequest,
    seller: Seller = Depends(get_current_seller),
):
    """Run the full RAG pipeline for a comment and return the preview reply."""
    settings = seller.bot_settings

    # Blacklist check
    blacklist = settings.get("blacklist_keywords", [])
    comment_lower = body.comment.lower()
    if any(kw.lower() in comment_lower for kw in blacklist):
        return TestReplyResponse(
            reply="[Bị chặn] Comment chứa từ khoá bị cấm.", intent="blacklist", chunks_used=[]
        )

    intent = detect_intent(body.comment)

    embed_provider = get_embed_provider()
    embedding = await embed_provider.embed(body.comment)

    chunks = await retriever.query(seller.id, embedding, n_results=3)
    context = "\n\n".join(c["content"] for c in chunks)
    system = SYSTEM_PROMPT_TEMPLATE.format(tone=settings.get("tone", "friendly"))

    reply_provider = get_reply_provider()
    reply = await reply_provider.generate_reply(
        system=system, context=context, user_msg=body.comment
    )

    return TestReplyResponse(
        reply=reply,
        intent=intent,
        chunks_used=[c["id"] for c in chunks],
    )
```

- [ ] **Step 3: Run settings tests**

Run: `cd backend && python3 -m pytest tests/test_settings_api.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/settings.py backend/app/schemas/settings.py
git commit -m "refactor: settings API uses seller from JWT"
```

---

## Task 10: Update Analytics API

**Files:**
- Modify: `backend/app/api/v1/analytics.py`

- [ ] **Step 1: Update analytics API**

Edit `backend/app/api/v1/analytics.py`:

```python
"""Analytics API — aggregated stats for a seller."""

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_seller
from app.database import get_db
from app.models.message import MessageLog
from app.models.seller import Seller
from app.models.session import LiveSession
from app.schemas.analytics import AnalyticsResponse

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    start_date: date | None = Query(
        default=None, description="Filter sessions from this date (inclusive)"
    ),
    end_date: date | None = Query(
        default=None, description="Filter sessions until this date (inclusive)"
    ),
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    # Base session filter - use seller.id from JWT
    session_filter = LiveSession.seller_id == seller.id

    # Add date filters if provided
    if start_date:
        start_datetime = datetime.combine(start_date, time.min)
        session_filter = session_filter & (LiveSession.started_at >= start_datetime)
    if end_date:
        end_datetime = datetime.combine(end_date, time.max)
        session_filter = session_filter & (LiveSession.started_at <= end_datetime)

    total_sessions = await db.scalar(select(func.count(LiveSession.id)).where(session_filter)) or 0

    session_subquery = select(LiveSession.id).where(session_filter).scalar_subquery()

    total_comments = (
        await db.scalar(
            select(func.count(MessageLog.id)).where(MessageLog.session_id.in_(session_subquery))
        )
        or 0
    )

    total_replies = (
        await db.scalar(
            select(func.count(MessageLog.id)).where(
                MessageLog.session_id.in_(session_subquery),
                MessageLog.reply.isnot(None),
            )
        )
        or 0
    )

    reply_rate = round((total_replies / total_comments * 100), 1) if total_comments > 0 else 0.0

    intent_rows = await db.execute(
        select(MessageLog.intent, func.count(MessageLog.id))
        .where(MessageLog.session_id.in_(session_subquery))
        .group_by(MessageLog.intent)
    )
    intent_breakdown = {row[0]: row[1] for row in intent_rows.all()}

    unanswered_count = (
        await db.scalar(
            select(func.count(MessageLog.id)).where(
                MessageLog.session_id.in_(session_subquery),
                MessageLog.reply.is_(None),
                MessageLog.intent.notin_(["skipped", "blacklist"]),
            )
        )
        or 0
    )

    return AnalyticsResponse(
        total_sessions=total_sessions,
        total_comments=total_comments,
        total_replies=total_replies,
        reply_rate=reply_rate,
        intent_breakdown=intent_breakdown,
        unanswered_count=unanswered_count,
    )
```

- [ ] **Step 2: Run analytics tests**

Run: `cd backend && python3 -m pytest tests/test_analytics_api.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/analytics.py
git commit -m "refactor: analytics API uses seller from JWT"
```

---

## Task 11: Update Sessions API

**Files:**
- Modify: `backend/app/api/v1/sessions.py`
- Modify: `backend/app/schemas/session.py`

- [ ] **Step 1: Update session schemas**

Edit `backend/app/schemas/session.py` - remove `seller_id` from `SessionStartRequest`:

```python
class SessionStartRequest(BaseModel):
    # Empty - seller comes from JWT
    pass
```

- [ ] **Step 2: Update sessions API**

This is the largest change. Edit `backend/app/api/v1/sessions.py`:

```python
"""Live Session API — start/stop/status/history + full RAG wiring."""

import asyncio
import logging
from datetime import datetime, timezone
from functools import partial
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_seller
from TikTokLive.client.client import TikTokLiveClient

from app.api.ws import broadcast
from app.core.ai.factory import get_embed_provider, get_reply_provider
from app.core.crypto import decrypt
from app.core.rag import retriever
from app.core.rag.pipeline import RAGPipeline
from app.core.session_state import get_session_state
from app.core.tiktok.listener import LiveListener
from app.core.tiktok.replier import Replier
from app.database import get_db, get_session_factory
from app.models.message import MessageLog
from app.models.seller import Seller
from app.models.session import LiveSession, SessionStatus
from app.schemas.session import (
    MessageLogResponse,
    SessionResponse,
    SessionStartRequest,
    SessionStatusResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


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


async def _handle_comment(seller_id: str, user: str, text: str) -> None:
    """Background callback: filter → RAG → save → reply → broadcast."""
    state = get_session_state(seller_id)

    if state.bot_paused or state.active_pipeline is None or state.active_session_id is None:
        return

    max_replies = state.active_pipeline.seller_settings.get("max_replies_per_session", 500)
    if state.reply_count >= max_replies:
        logger.info("max_replies_per_session reached (%d), skipping", max_replies)
        return

    # Save incoming comment
    message_id: str | None = None
    async with get_session_factory()() as db:
        msg = MessageLog(
            session_id=state.active_session_id,
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
    await broadcast(
        seller_id,
        {
            "type": "comment",
            "message_id": message_id,
            "user": user,
            "content": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    # Run RAG pipeline
    result = await state.active_pipeline.process(user, text)

    if result.skipped or result.reply is None:
        async with get_session_factory()() as db:
            msg = await db.get(MessageLog, message_id)
            if msg:
                msg.intent = result.intent
                await db.commit()
        return

    # Send reply via replier (with throttle)
    try:
        if state.active_replier is not None:
            await state.active_replier.send(result.reply)
        state.reply_count += 1
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
    await broadcast(
        seller_id,
        {
            "type": "reply",
            "message_id": message_id,
            "content": result.reply,
            "intent": result.intent,
            "chunks_used": result.chunks_used,
        }
    )


async def _handle_disconnect(seller_id: str) -> None:
    """Callback when TikTok stream ends or connection drops."""
    state = get_session_state(seller_id)

    logger.info("TikTok disconnect — marking session ended for seller %s", seller_id)
    if state.active_session_id:
        async with get_session_factory()() as db:
            session = await db.get(LiveSession, state.active_session_id)
            if session:
                session.status = SessionStatus.ENDED
                session.ended_at = datetime.now(timezone.utc)
                await db.commit()

    await broadcast(seller_id, {"type": "status", "connected": False})
    state.reset()


# ── API Endpoints ─────────────────────────────────────────────────────────────


@router.post("/start", response_model=SessionStatusResponse)
async def start_session(
    body: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
) -> SessionStatusResponse:
    state = get_session_state(seller.id)

    if state.active_session_id is not None:
        raise HTTPException(status_code=400, detail="A session is already active. Stop it first.")

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

    # Register callbacks with seller_id bound
    listener.on_comment(partial(_handle_comment, seller.id))
    listener.on_disconnect(partial(_handle_disconnect, seller.id))

    # Create DB session record
    live_session = LiveSession(seller_id=seller.id, status=SessionStatus.ACTIVE)
    db.add(live_session)
    await db.commit()
    await db.refresh(live_session)

    # Store state
    state.active_session_id = live_session.id
    state.active_listener = listener
    state.active_replier = replier
    state.active_pipeline = pipeline
    state.bot_paused = False
    state.reply_count = 0

    # Start listener in background (non-blocking)
    task = asyncio.create_task(listener.start(), name=f"tiktok-listener-{seller.id}")
    task.add_done_callback(
        lambda t: (
            logger.exception("Listener task crashed", exc_info=t.exception())
            if not t.cancelled() and t.exception()
            else None
        )
    )
    state.active_task = task

    await broadcast(seller.id, {"type": "status", "connected": True, "room_id": None})
    logger.info("Session started: %s for seller %s", live_session.id, seller.id)

    return SessionStatusResponse(
        connected=True, session=SessionResponse.model_validate(live_session)
    )


@router.post("/stop")
async def stop_session(
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
) -> dict[str, str]:
    state = get_session_state(seller.id)

    if state.active_session_id is None:
        raise HTTPException(status_code=400, detail="No active session")

    if state.active_task is not None and not state.active_task.done():
        state.active_task.cancel()

    if state.active_listener is not None:
        try:
            await state.active_listener.stop()
        except Exception:
            logger.exception("Error stopping listener")

    session = await db.get(LiveSession, state.active_session_id)
    if session:
        session.status = SessionStatus.ENDED
        session.ended_at = datetime.now(timezone.utc)
        await db.commit()

    state.reset()

    await broadcast(seller.id, {"type": "status", "connected": False})
    return {"message": "Session stopped"}


@router.get("/status", response_model=SessionStatusResponse)
async def get_status(
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
) -> SessionStatusResponse:
    state = get_session_state(seller.id)

    if state.active_session_id is None:
        return SessionStatusResponse(connected=False, session=None)

    result = await db.execute(select(LiveSession).where(LiveSession.id == state.active_session_id))
    session = result.scalar_one_or_none()
    if session is None or session.status != SessionStatus.ACTIVE:
        return SessionStatusResponse(connected=False, session=None)

    return SessionStatusResponse(connected=True, session=SessionResponse.model_validate(session))


@router.get("/history", response_model=list[SessionResponse])
async def get_history(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
) -> list[SessionResponse]:
    offset = (page - 1) * limit
    result = await db.execute(
        select(LiveSession)
        .where(LiveSession.seller_id == seller.id)
        .order_by(LiveSession.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    sessions = result.scalars().all()
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get("/{session_id}/messages", response_model=list[MessageLogResponse])
async def get_session_messages(
    session_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
) -> list[MessageLogResponse]:
    session = await db.get(LiveSession, session_id)
    if session is None or session.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Session not found")

    offset = (page - 1) * limit
    result = await db.execute(
        select(MessageLog)
        .where(MessageLog.session_id == session_id)
        .order_by(MessageLog.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return [MessageLogResponse.model_validate(m) for m in result.scalars().all()]
```

- [ ] **Step 3: Run session tests**

Run: `cd backend && python3 -m pytest tests/test_session_wiring.py tests/test_sessions_api.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/sessions.py backend/app/schemas/session.py
git commit -m "refactor: sessions API uses seller from JWT, isolated state per seller"
```

---

## Task 12: Update WebSocket for Multi-Tenant

**Files:**
- Modify: `backend/app/api/ws.py`

- [ ] **Step 1: Update ws.py for isolated connections**

Edit `backend/app/api/ws.py`:

```python
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.session_state import get_session_state

logger = logging.getLogger(__name__)
router = APIRouter()

# Multi-tenant connections: seller_id -> set of websockets
_connections: dict[str, list[WebSocket]] = {}


async def broadcast(seller_id: str, message: dict[str, Any]) -> None:
    """Send a message to all connected dashboard clients for a seller."""
    if seller_id not in _connections:
        return

    dead = []
    for ws in _connections[seller_id]:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead.append(ws)

    for ws in dead:
        _connections[seller_id].remove(ws)


@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    # Auth via cookie
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=1008)
        return

    from app.core.security import decode_access_token

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=1008)
        return

    seller_id = payload.get("sub")
    if not seller_id:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    # Add to seller's connection pool
    if seller_id not in _connections:
        _connections[seller_id] = []
    _connections[seller_id].append(websocket)

    total = sum(len(conns) for conns in _connections.values())
    logger.info("Dashboard client connected for seller %s (%d total)", seller_id, total)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from WS client, ignoring")
                continue

            msg_type = msg.get("type")
            logger.info("WS command received from seller %s: %s", seller_id, msg_type)

            state = get_session_state(seller_id)

            if msg_type == "pause_bot":
                state.bot_paused = True
                await broadcast(seller_id, {"type": "status", "paused": True})

            elif msg_type == "resume_bot":
                state.bot_paused = False
                await broadcast(seller_id, {"type": "status", "paused": False})

            elif msg_type == "manual_reply":
                await _handle_manual_reply(seller_id, msg)

    except WebSocketDisconnect:
        if seller_id in _connections and websocket in _connections[seller_id]:
            _connections[seller_id].remove(websocket)
        total = sum(len(conns) for conns in _connections.values())
        logger.info("Dashboard client disconnected (%d remaining)", total)
    except Exception:
        logger.exception("WebSocket error")
        if seller_id in _connections and websocket in _connections[seller_id]:
            _connections[seller_id].remove(websocket)


async def _handle_manual_reply(seller_id: str, msg: dict) -> None:
    """Send a manual reply for a specific message_id via the active replier."""
    from app.database import get_session_factory
    from app.models.message import MessageLog

    message_id = msg.get("message_id")
    content = msg.get("content", "").strip()

    if not message_id or not content:
        logger.warning("manual_reply missing message_id or content")
        return

    state = get_session_state(seller_id)
    replier = state.active_replier
    if replier is None:
        await broadcast(seller_id, {"type": "error", "message": "No active session"})
        return

    try:
        await replier.send(content)
    except Exception as exc:
        logger.exception("manual_reply send failed")
        await broadcast(seller_id, {"type": "error", "message": str(exc)})
        return

    async with get_session_factory()() as db:
        log = await db.get(MessageLog, message_id)
        if log:
            log.reply = content
            log.intent = "manual"
            await db.commit()

    await broadcast(
        seller_id,
        {
            "type": "reply",
            "message_id": message_id,
            "content": content,
            "intent": "manual",
            "chunks_used": [],
        }
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/ws.py
git commit -m "refactor: WebSocket connections isolated per seller"
```

---

## Task 13: Create Seller Management CLI

**Files:**
- Create: `backend/scripts/manage_seller.py`

- [ ] **Step 1: Create scripts directory if needed**

Run: `mkdir -p backend/scripts`

- [ ] **Step 2: Create manage_seller.py**

Create `backend/scripts/manage_seller.py`:

```python
#!/usr/bin/env python3
"""CLI tool for managing sellers."""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import get_settings
from app.core.crypto import encrypt
from app.core.security import hash_password
from app.database import Base
from app.models.seller import Seller


async def get_db_session():
    """Create database session."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return session_factory()


async def create_seller(args):
    """Create a new seller."""
    password = args.password or getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("Error: Passwords do not match")
        return 1

    async with await get_db_session() as db:
        # Check if username exists
        result = await db.execute(select(Seller).where(Seller.username == args.username))
        if result.scalar_one_or_none():
            print(f"Error: Username '{args.username}' already exists")
            return 1

        seller = Seller(
            name=args.name,
            username=args.username,
            password_hash=hash_password(password),
            tiktok_unique_id=args.tiktok_id,
            tiktok_session_id_encrypted=encrypt(args.session_id),
            tiktok_target_idc_encrypted=encrypt(args.target_idc),
        )
        db.add(seller)
        await db.commit()
        await db.refresh(seller)

        print(f"Created seller: {seller.name} (id={seller.id})")
        return 0


async def set_password(args):
    """Set/reset password for existing seller."""
    async with await get_db_session() as db:
        result = await db.execute(select(Seller).where(Seller.username == args.username))
        seller = result.scalar_one_or_none()

        if not seller:
            print(f"Error: Seller '{args.username}' not found")
            return 1

        password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm password: ")

        if password != confirm:
            print("Error: Passwords do not match")
            return 1

        seller.password_hash = hash_password(password)
        await db.commit()

        print(f"Password updated for seller: {seller.username}")
        return 0


async def list_sellers(args):
    """List all sellers."""
    async with await get_db_session() as db:
        result = await db.execute(select(Seller).order_by(Seller.created_at.desc()))
        sellers = result.scalars().all()

        if not sellers:
            print("No sellers found")
            return 0

        print(f"{'ID':<36} {'Username':<20} {'Name':<30} {'Active':<8} {'TikTok ID':<20}")
        print("-" * 120)
        for s in sellers:
            active = "Yes" if s.is_active else "No"
            print(f"{s.id:<36} {s.username:<20} {s.name:<30} {active:<8} {s.tiktok_unique_id:<20}")

        return 0


async def disable_seller(args):
    """Disable a seller account."""
    async with await get_db_session() as db:
        result = await db.execute(select(Seller).where(Seller.username == args.username))
        seller = result.scalar_one_or_none()

        if not seller:
            print(f"Error: Seller '{args.username}' not found")
            return 1

        seller.is_active = False
        await db.commit()

        print(f"Disabled seller: {seller.username}")
        return 0


async def enable_seller(args):
    """Enable a seller account."""
    async with await get_db_session() as db:
        result = await db.execute(select(Seller).where(Seller.username == args.username))
        seller = result.scalar_one_or_none()

        if not seller:
            print(f"Error: Seller '{args.username}' not found")
            return 1

        seller.is_active = True
        await db.commit()

        print(f"Enabled seller: {seller.username}")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Seller management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    create_parser = subparsers.add_parser("create", help="Create a new seller")
    create_parser.add_argument("--username", required=True, help="Login username")
    create_parser.add_argument("--password", help="Password (will prompt if not provided)")
    create_parser.add_argument("--name", required=True, help="Display name")
    create_parser.add_argument("--tiktok-id", required=True, help="TikTok unique ID (e.g. @username)")
    create_parser.add_argument("--session-id", required=True, help="TikTok session ID")
    create_parser.add_argument("--target-idc", required=True, help="TikTok target IDC")

    # set-password
    setpw_parser = subparsers.add_parser("set-password", help="Set/reset seller password")
    setpw_parser.add_argument("--username", required=True, help="Seller username")

    # list
    subparsers.add_parser("list", help="List all sellers")

    # disable
    disable_parser = subparsers.add_parser("disable", help="Disable a seller account")
    disable_parser.add_argument("--username", required=True, help="Seller username")

    # enable
    enable_parser = subparsers.add_parser("enable", help="Enable a seller account")
    enable_parser.add_argument("--username", required=True, help="Seller username")

    args = parser.parse_args()

    commands = {
        "create": create_seller,
        "set-password": set_password,
        "list": list_sellers,
        "disable": disable_seller,
        "enable": enable_seller,
    }

    exit_code = asyncio.run(commands[args.command](args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Make executable**

Run: `chmod +x backend/scripts/manage_seller.py`

- [ ] **Step 4: Test CLI help**

Run: `cd backend && python3 scripts/manage_seller.py --help`
Expected: Shows help with create, set-password, list, disable, enable commands

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/manage_seller.py
git commit -m "feat: add seller management CLI tool"
```

---

## Task 14: Update Frontend API Client

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/.env.example`

- [ ] **Step 1: Update frontend/lib/api.ts**

Remove `SELLER_ID` and update types:

```typescript
// lib/api.ts — typed REST client for the TikTok Live AI Bot backend

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types (mirror backend Pydantic schemas) ──────────────────────────────────

export type KnowledgeCategory = "product" | "policy" | "faq";

export interface KnowledgeChunk {
  id: string;
  seller_id: string;
  content: string;
  category: KnowledgeCategory;
  metadata: Record<string, unknown>;
  needs_reembed: boolean;
}

export interface KnowledgeList {
  items: KnowledgeChunk[];
  total: number;
  page: number;
  limit: number;
}

export interface UploadResult {
  created: number;
  skipped: number;
  errors: string[];
}

export interface PreviewRow {
  row: number;
  content: string;
  category: string;
  is_valid: boolean;
  warning: string | null;
}

export interface CsvPreview {
  total_rows: number;
  valid_rows: number;
  preview: PreviewRow[];
  warnings: string[];
}

export type SessionStatus = "active" | "ended" | "paused";

export interface Session {
  id: string;
  seller_id: string;
  tiktok_room_id?: number;
  status: SessionStatus;
  started_at: string;
  ended_at?: string;
}

export interface SessionState {
  connected: boolean;
  session: Session | null;
}

export interface BotSettings {
  tone: string;
  blacklist_keywords: string[];
  reply_delay_min: number;
  reply_delay_max: number;
  user_cooldown_seconds: number;
  max_replies_per_session: number;
  auto_reply_enabled: boolean;
}

export interface BotSettingsUpdate {
  tone?: string;
  blacklist_keywords?: string[];
  reply_delay_min?: number;
  reply_delay_max?: number;
  user_cooldown_seconds?: number;
  max_replies_per_session?: number;
  auto_reply_enabled?: boolean;
}

export interface TestReplyResult {
  reply: string;
  intent: string;
  chunks_used: string[];
}

// Analytics
export interface AnalyticsData {
  total_sessions: number;
  total_comments: number;
  total_replies: number;
  reply_rate: number;
  intent_breakdown: Record<string, number>;
  unanswered_count: number;
}

// Message log
export interface MessageLog {
  id: string;
  session_id: string;
  user_unique_id: string;
  comment: string;
  reply: string | null;
  intent: string;
  chunks_used: string[];
  created_at: string;
}

// Auth - updated for multi-tenant
export interface AuthSeller {
  id: string;
  username: string;
  name: string;
  tiktok_unique_id: string;
}

// ── Error type ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Core fetch wrapper ───────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_URL}${path}`;
  const isFormData = options.body instanceof FormData;
  const res = await fetch(url, {
    credentials: "include",
    headers: isFormData
      ? (options.headers ?? {})
      : { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.detail ?? body.message ?? message;
    } catch {
      // ignore parse error
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

function qs(params: Record<string, string | number>): string {
  const filtered = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (filtered.length === 0) return "";
  const p = new URLSearchParams(filtered.map(([k, v]) => [k, String(v)]));
  return `?${p.toString()}`;
}

// ── API surface ──────────────────────────────────────────────────────────────

export const api = {
  knowledge: {
    list(params: { page?: number; limit?: number } = {}): Promise<KnowledgeList> {
      const { page = 1, limit = 20 } = params;
      return request(`/api/v1/knowledge/${qs({ page, limit })}`, {
        method: "GET",
      });
    },

    create(body: {
      content: string;
      category: KnowledgeCategory;
      metadata: Record<string, unknown>;
    }): Promise<KnowledgeChunk> {
      return request("/api/v1/knowledge/", {
        method: "POST",
        body: JSON.stringify(body),
      });
    },

    update(
      id: string,
      body: {
        content?: string;
        category?: KnowledgeCategory;
        metadata?: Record<string, unknown>;
      },
    ): Promise<KnowledgeChunk> {
      return request(`/api/v1/knowledge/${id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      });
    },

    delete(id: string): Promise<void> {
      return request(`/api/v1/knowledge/${id}`, { method: "DELETE" });
    },

    preview(file: File): Promise<CsvPreview> {
      const form = new FormData();
      form.append("file", file);
      return request("/api/v1/knowledge/preview", { method: "POST", body: form });
    },

    upload(file: File): Promise<UploadResult> {
      const form = new FormData();
      form.append("file", file);
      return request("/api/v1/knowledge/upload", {
        method: "POST",
        body: form,
      });
    },
  },

  sessions: {
    start(): Promise<SessionState> {
      return request("/api/v1/sessions/start", {
        method: "POST",
        body: JSON.stringify({}),
      });
    },

    stop(): Promise<{ message: string }> {
      return request("/api/v1/sessions/stop", { method: "POST" });
    },

    status(): Promise<SessionState> {
      return request("/api/v1/sessions/status", { method: "GET" });
    },

    history(params: { page?: number; limit?: number } = {}): Promise<Session[]> {
      const { page = 1, limit = 20 } = params;
      return request(
        `/api/v1/sessions/history${qs({ page, limit })}`,
        { method: "GET" },
      );
    },

    messages(sessionId: string, params: { page?: number; limit?: number } = {}): Promise<MessageLog[]> {
      const { page = 1, limit = 50 } = params;
      return request(
        `/api/v1/sessions/${sessionId}/messages${qs({ page, limit })}`,
        { method: "GET" },
      );
    },
  },

  settings: {
    get(): Promise<BotSettings> {
      return request("/api/v1/settings/", { method: "GET" });
    },

    update(body: BotSettingsUpdate): Promise<BotSettings> {
      return request("/api/v1/settings/", {
        method: "PUT",
        body: JSON.stringify(body),
      });
    },

    testReply(comment: string): Promise<TestReplyResult> {
      return request("/api/v1/settings/test-reply", {
        method: "POST",
        body: JSON.stringify({ comment }),
      });
    },
  },

  analytics: {
    get(params: { start_date?: string; end_date?: string } = {}): Promise<AnalyticsData> {
      const queryParams: Record<string, string | number> = {};
      if (params.start_date) queryParams.start_date = params.start_date;
      if (params.end_date) queryParams.end_date = params.end_date;
      return request(`/api/v1/analytics/${qs(queryParams)}`, {
        method: "GET",
      });
    },
  },

  auth: {
    login(username: string, password: string): Promise<AuthSeller> {
      return request("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
    },

    logout(): Promise<{ message: string }> {
      return request("/api/v1/auth/logout", { method: "POST" });
    },

    me(): Promise<AuthSeller> {
      return request("/api/v1/auth/me", { method: "GET" });
    },
  },
};
```

- [ ] **Step 2: Update frontend/.env.example**

Edit `frontend/.env.example` - remove SELLER_ID:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts frontend/.env.example
git commit -m "refactor: remove SELLER_ID from frontend, use seller from JWT"
```

---

## Task 15: Update Frontend Sidebar with Seller Name

**Files:**
- Modify: `frontend/components/nav/Sidebar.tsx`

- [ ] **Step 1: Update Sidebar to show seller name**

Edit `frontend/components/nav/Sidebar.tsx`:

```tsx
"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BarChart2, BookOpen, History, LogOut, Radio, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { api, AuthSeller, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const links = [
  { href: "/knowledge", label: "Knowledge Base", icon: BookOpen },
  { href: "/monitor", label: "Live Monitor", icon: Radio },
  { href: "/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/sessions", label: "Sessions", icon: History },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [seller, setSeller] = useState<AuthSeller | null>(null);

  useEffect(() => {
    api.auth.me()
      .then(setSeller)
      .catch(() => setSeller(null));
  }, []);

  async function handleLogout() {
    try {
      await api.auth.logout();
    } catch (err) {
      // Ignore errors
    }
    router.push("/login");
    router.refresh();
  }

  // Don't render sidebar on login page
  if (pathname === "/login") {
    return null;
  }

  return (
    <aside className="flex h-screen w-56 flex-col border-r bg-slate-50 px-3 py-6 shrink-0">
      <div className="mb-8 px-2">
        <h1 className="text-lg font-bold tracking-tight">TikTok Live Bot</h1>
        {seller && (
          <p className="text-sm text-slate-500 truncate" title={seller.name}>
            {seller.name}
          </p>
        )}
      </div>
      <nav className="flex flex-col gap-1 flex-1">
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              pathname.startsWith(href)
                ? "bg-slate-200 text-slate-900"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>
      <div className="border-t pt-4">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 text-slate-600 hover:text-slate-900"
          onClick={handleLogout}
        >
          <LogOut className="h-4 w-4" />
          Logout
        </Button>
      </div>
    </aside>
  );
}
```

- [ ] **Step 2: Run frontend build to verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/components/nav/Sidebar.tsx
git commit -m "feat: show seller name in sidebar, add logout button"
```

---

## Task 16: Update docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Remove NEXT_PUBLIC_SELLER_ID**

Edit `docker-compose.yml` - remove any `NEXT_PUBLIC_SELLER_ID` references from frontend service.

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "chore: remove NEXT_PUBLIC_SELLER_ID from docker-compose"
```

---

## Task 17: Run All Tests

**Files:** None (verification)

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python3 -m pytest tests/ -v`
Expected: All tests pass (except pre-existing AI provider issues)

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && npm test`
Expected: All tests pass

- [ ] **Step 3: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

---

## Task 18: Final Integration Test

**Files:** None (manual testing)

- [ ] **Step 1: Start backend**

Run: `cd backend && uvicorn app.main:app --reload`

- [ ] **Step 2: Run migration**

Run: `cd backend && alembic upgrade head`

- [ ] **Step 3: Create test seller via CLI**

Run: 
```bash
cd backend && python3 scripts/manage_seller.py create \
  --username "testshop" \
  --name "Test Shop" \
  --tiktok-id "@testshop" \
  --session-id "test_session_id" \
  --target-idc "useast1a"
```
Enter password when prompted.

- [ ] **Step 4: Start frontend**

Run: `cd frontend && npm run dev`

- [ ] **Step 5: Test login flow**

1. Navigate to http://localhost:3000
2. Should redirect to /login
3. Login with testshop credentials
4. Should see seller name in sidebar
5. Navigate between pages
6. Logout should work

- [ ] **Step 6: Commit any final fixes**

If any issues found, fix and commit.

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add auth fields to Seller model | seller.py |
| 2 | Create Alembic migration | alembic/versions/ |
| 3 | Add password hashing | security.py |
| 4 | Update auth schemas | schemas/auth.py |
| 5 | Implement seller auth | api/v1/auth.py |
| 6 | Update test fixtures | conftest.py |
| 7 | Multi-tenant session state | session_state.py |
| 8 | Update knowledge API | knowledge.py |
| 9 | Update settings API | settings.py |
| 10 | Update analytics API | analytics.py |
| 11 | Update sessions API | sessions.py |
| 12 | Update WebSocket | ws.py |
| 13 | Create CLI tool | manage_seller.py |
| 14 | Update frontend API client | lib/api.ts |
| 15 | Update sidebar | Sidebar.tsx |
| 16 | Update docker-compose | docker-compose.yml |
| 17 | Run all tests | - |
| 18 | Integration test | - |
