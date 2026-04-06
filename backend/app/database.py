from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, echo=False)
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(_get_engine(), expire_on_commit=False)
    return _session_factory


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Public accessor for background tasks that need their own DB session."""
    return _get_session_factory()


async def get_db() -> AsyncSession:
    async with _get_session_factory()() as session:
        yield session


async def create_tables() -> None:
    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
