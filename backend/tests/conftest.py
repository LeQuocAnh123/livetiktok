import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.database import Base, get_db

# Import all models so Base.metadata knows about every table before create_all
import app.models.seller  # noqa: F401
import app.models.session  # noqa: F401
import app.models.message  # noqa: F401

_TEST_SELLER_ID = "test-seller-001"


@pytest.fixture(scope="function")
async def db_session():
    # Use temp file instead of in-memory to avoid connection isolation issues
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()
    finally:
        os.unlink(db_path)


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
    from app.core.crypto import encrypt

    seller = Seller(
        id=_TEST_SELLER_ID,
        name="Test Shop",
        username="testshop",
        password_hash=hash_password("testpass123"),
        is_active=True,
        tiktok_unique_id="@testshop",
        tiktok_session_id_encrypted=encrypt("test-session-123"),
        tiktok_target_idc_encrypted=encrypt("useast1a"),
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
        from app.core.security import create_access_token
        from app.main import app

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
