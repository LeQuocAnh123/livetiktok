"""Tests for _handle_gift session wiring — DB save, broadcast, LLM reply, TikTok send."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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
        return_value=GiftReplyResult(reply="Cam on ban!", sentiment="positive")
    )
    state.active_pipeline.seller_settings = {"auto_reply_enabled": True}
    state.bot_paused = False

    return session, state


@pytest.mark.asyncio
async def test_handle_gift_saves_gift_log(db_session, test_seller, active_session):
    """_handle_gift saves a GiftLog record to the database."""
    session, state = active_session

    with (
        patch("app.api.v1.sessions.get_session_factory") as mock_factory,
        patch("app.api.v1.sessions.broadcast", new_callable=AsyncMock) as mock_broadcast,
    ):
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
    assert gifts[0].thank_reply == "Cam on ban!"


@pytest.mark.asyncio
async def test_handle_gift_broadcasts_gift_and_reply(db_session, test_seller, active_session):
    """_handle_gift broadcasts both 'gift' and 'gift_reply' WebSocket messages."""
    session, state = active_session

    with (
        patch("app.api.v1.sessions.get_session_factory") as mock_factory,
        patch("app.api.v1.sessions.broadcast", new_callable=AsyncMock) as mock_broadcast,
    ):
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

    with (
        patch("app.api.v1.sessions.get_session_factory") as mock_factory,
        patch("app.api.v1.sessions.broadcast", new_callable=AsyncMock) as mock_broadcast,
    ):
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
