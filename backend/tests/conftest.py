from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.database import Base, get_db

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
        is_active=True,
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
