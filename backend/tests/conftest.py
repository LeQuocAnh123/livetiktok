from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.database import Base, get_db

_ANALYTICS_SELLER_ID = "analytics-seller-001"

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


@pytest.fixture
async def seller_id(db_session) -> str:
    """Insert a bare-minimum Seller row and return its ID."""
    from app.models.seller import Seller

    seller = Seller(
        id=_ANALYTICS_SELLER_ID,
        name="Analytics Test Seller",
        tiktok_unique_id="analytics_test",
        tiktok_session_id_encrypted="enc_session",
        tiktok_target_idc_encrypted="enc_idc",
    )
    db_session.add(seller)
    await db_session.commit()
    return _ANALYTICS_SELLER_ID


@pytest.fixture(autouse=True)
def reset_session_state():
    """Reset all module-level session state between tests."""
    import app.api.v1.sessions as sessions_module
    # Reset all Plan 1 + Plan 2 globals
    sessions_module._active_session_id = None
    sessions_module._active_listener = None
    sessions_module._active_replier = None
    sessions_module._active_pipeline = None
    sessions_module._active_task = None
    sessions_module._bot_paused = False
    sessions_module._reply_count = 0
    yield
    sessions_module._active_session_id = None
    sessions_module._active_listener = None
    sessions_module._active_replier = None
    sessions_module._active_pipeline = None
    sessions_module._active_task = None
    sessions_module._bot_paused = False
    sessions_module._reply_count = 0
