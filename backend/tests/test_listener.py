from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.tiktok.listener import LiveListener, ListenerEvent


@pytest.fixture
def mock_tiktok_client():
    client = MagicMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.is_live = AsyncMock(return_value=True)
    client.on = MagicMock(side_effect=lambda event_type: lambda fn: fn)
    return client


def test_listener_event_enum():
    assert ListenerEvent.COMMENT == "comment"
    assert ListenerEvent.DISCONNECT == "disconnect"


async def test_on_comment_calls_handler(mock_tiktok_client):
    received = []
    listener = LiveListener(client=mock_tiktok_client)
    listener.on_comment(lambda user, text: received.append((user, text)))

    # Simulate firing the comment handler directly
    await listener._handle_comment_event(
        MagicMock(user_info=MagicMock(unique_id="user1"), comment="hello")
    )
    assert received == [("user1", "hello")]


async def test_on_disconnect_calls_handler(mock_tiktok_client):
    disconnected = []
    listener = LiveListener(client=mock_tiktok_client)
    listener.on_disconnect(lambda: disconnected.append(True))

    await listener._handle_disconnect_event(MagicMock())
    assert disconnected == [True]
