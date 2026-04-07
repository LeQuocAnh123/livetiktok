"""Tests for MessageLog model with sentiment field."""

import pytest

from app.models.message import MessageLog
from app.models.session import LiveSession, SessionStatus


@pytest.mark.asyncio
async def test_message_log_default_sentiment(db_session, test_seller):
    """MessageLog defaults sentiment to 'neutral'."""
    session = LiveSession(seller_id=test_seller.id, status=SessionStatus.ACTIVE)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    msg = MessageLog(
        session_id=session.id,
        user_unique_id="viewer1",
        comment="Hello",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)

    assert msg.sentiment == "neutral"


@pytest.mark.asyncio
async def test_message_log_explicit_sentiment(db_session, test_seller):
    """MessageLog stores explicit sentiment value."""
    session = LiveSession(seller_id=test_seller.id, status=SessionStatus.ACTIVE)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    msg = MessageLog(
        session_id=session.id,
        user_unique_id="viewer2",
        comment="Giao hàng chậm quá!",
        sentiment="negative",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)

    assert msg.sentiment == "negative"
