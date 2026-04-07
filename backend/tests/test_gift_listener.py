"""Tests for LiveListener GiftEvent handling and streak filtering."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.tiktok.listener import LiveListener


def _make_mock_client():
    """Create a mock TikTokLiveClient that captures event registrations."""
    client = MagicMock()
    client._events = {}

    def on_decorator(event_class):
        def decorator(fn):
            # Use id as key since patched classes may not have __name__
            client._events[id(event_class)] = fn
            return fn

        return decorator

    client.on = on_decorator
    return client


def _make_gift_event(unique_id, gift_name, diamond_count, repeat_count, streakable, streaking):
    """Create a mock GiftEvent."""
    event = MagicMock()
    event.user.unique_id = unique_id
    event.gift.name = gift_name
    event.gift.diamond_count = diamond_count
    event.gift.streakable = streakable
    event.repeat_count = repeat_count
    event.repeat_end = not streaking if streakable else True
    event.streaking = streaking
    event.value = None if streaking else repeat_count * diamond_count * 0.005
    return event


@pytest.mark.asyncio
async def test_gift_handler_called_for_non_streakable():
    """Non-streakable gifts are dispatched immediately."""
    client = _make_mock_client()

    with patch("app.core.tiktok.listener.GiftEvent"):
        listener = LiveListener(client)

    handler = AsyncMock()
    listener.on_gift(handler)

    event = _make_gift_event("viewer1", "Lion", 500, 1, streakable=False, streaking=False)
    await listener._handle_gift_event(event)

    handler.assert_called_once_with("viewer1", "Lion", 500, 1)


@pytest.mark.asyncio
async def test_gift_handler_called_when_streak_ends():
    """Streakable gifts dispatch only when streak ends (streaking=False)."""
    client = _make_mock_client()

    with patch("app.core.tiktok.listener.GiftEvent"):
        listener = LiveListener(client)

    handler = AsyncMock()
    listener.on_gift(handler)

    event = _make_gift_event("viewer2", "Rose", 1, 10, streakable=True, streaking=False)
    await listener._handle_gift_event(event)

    handler.assert_called_once_with("viewer2", "Rose", 1, 10)


@pytest.mark.asyncio
async def test_gift_handler_skipped_during_streak():
    """Streakable gifts are skipped while streak is ongoing."""
    client = _make_mock_client()

    with patch("app.core.tiktok.listener.GiftEvent"):
        listener = LiveListener(client)

    handler = AsyncMock()
    listener.on_gift(handler)

    event = _make_gift_event("viewer3", "Rose", 1, 3, streakable=True, streaking=True)
    await listener._handle_gift_event(event)

    handler.assert_not_called()


@pytest.mark.asyncio
async def test_on_gift_registers_handler():
    """on_gift() registers a handler in the gift handlers list."""
    client = _make_mock_client()

    with patch("app.core.tiktok.listener.GiftEvent"):
        listener = LiveListener(client)

    handler = AsyncMock()
    listener.on_gift(handler)

    assert handler in listener._gift_handlers
