"""Tests for fetching recent seller override examples."""

import pytest

from app.core.rag.overrides import get_recent_overrides
from app.models.message import MessageLog
from app.models.session import LiveSession, SessionStatus


@pytest.mark.asyncio
async def test_get_recent_overrides_returns_manual_replies(db_session, test_seller):
    """Fetches manual override (comment, reply) pairs for a seller."""
    session = LiveSession(seller_id=test_seller.id, status=SessionStatus.ACTIVE)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # Create a manual override message
    msg = MessageLog(
        session_id=session.id,
        user_unique_id="viewer1",
        comment="Giá bao nhiêu?",
        reply="Dạ 150k thôi ạ!",
        intent="manual",
    )
    db_session.add(msg)
    await db_session.commit()

    overrides = await get_recent_overrides(test_seller.id, db_session, limit=5)

    assert len(overrides) == 1
    assert overrides[0] == ("Giá bao nhiêu?", "Dạ 150k thôi ạ!")


@pytest.mark.asyncio
async def test_get_recent_overrides_excludes_bot_replies(db_session, test_seller):
    """Only returns messages with intent='manual', not bot-generated replies."""
    session = LiveSession(seller_id=test_seller.id, status=SessionStatus.ACTIVE)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # Bot reply (intent != "manual")
    bot_msg = MessageLog(
        session_id=session.id,
        user_unique_id="viewer1",
        comment="Hello",
        reply="Chào bạn!",
        intent="greeting",
    )
    # Manual override
    manual_msg = MessageLog(
        session_id=session.id,
        user_unique_id="viewer2",
        comment="Ship lâu không?",
        reply="Dạ 2-3 ngày ạ!",
        intent="manual",
    )
    db_session.add_all([bot_msg, manual_msg])
    await db_session.commit()

    overrides = await get_recent_overrides(test_seller.id, db_session, limit=5)

    assert len(overrides) == 1
    assert overrides[0][0] == "Ship lâu không?"


@pytest.mark.asyncio
async def test_get_recent_overrides_respects_limit(db_session, test_seller):
    """Returns at most `limit` overrides, most recent first."""
    session = LiveSession(seller_id=test_seller.id, status=SessionStatus.ACTIVE)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    for i in range(10):
        msg = MessageLog(
            session_id=session.id,
            user_unique_id=f"viewer{i}",
            comment=f"Question {i}",
            reply=f"Answer {i}",
            intent="manual",
        )
        db_session.add(msg)
    await db_session.commit()

    overrides = await get_recent_overrides(test_seller.id, db_session, limit=5)

    assert len(overrides) == 5


@pytest.mark.asyncio
async def test_get_recent_overrides_empty_for_new_seller(db_session, test_seller):
    """Returns empty list when seller has no manual overrides."""
    overrides = await get_recent_overrides(test_seller.id, db_session, limit=5)
    assert overrides == []


@pytest.mark.asyncio
async def test_get_recent_overrides_excludes_other_sellers(db_session, test_seller):
    """Only returns overrides from the specified seller, not other sellers."""
    # Create a session for test_seller
    session = LiveSession(seller_id=test_seller.id, status=SessionStatus.ACTIVE)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    msg = MessageLog(
        session_id=session.id,
        user_unique_id="viewer1",
        comment="My question",
        reply="My answer",
        intent="manual",
    )
    db_session.add(msg)

    # Create a session for a different seller
    other_session = LiveSession(seller_id="other-seller-id", status=SessionStatus.ACTIVE)
    db_session.add(other_session)
    await db_session.commit()
    await db_session.refresh(other_session)

    other_msg = MessageLog(
        session_id=other_session.id,
        user_unique_id="viewer2",
        comment="Other question",
        reply="Other answer",
        intent="manual",
    )
    db_session.add(other_msg)
    await db_session.commit()

    overrides = await get_recent_overrides(test_seller.id, db_session, limit=5)

    assert len(overrides) == 1
    assert overrides[0][0] == "My question"
