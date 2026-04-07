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

    result = await db_session.execute(select(GL).where(GL.session_id == session.id))
    gifts = result.scalars().all()
    assert len(gifts) == 1
    assert gifts[0].gift_name == "Sunglasses"
