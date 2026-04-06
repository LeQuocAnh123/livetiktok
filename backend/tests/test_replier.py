import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.tiktok.replier import Replier


@pytest.fixture
def mock_web_client():
    client = MagicMock()
    client.send_room_chat = AsyncMock(return_value={"status": "ok"})
    return client


async def test_send_applies_throttle(mock_web_client):
    replier = Replier(web_client=mock_web_client, delay_min=0.1, delay_max=0.2)
    start = time.monotonic()
    await replier.send("hello")
    elapsed = time.monotonic() - start
    assert elapsed >= 0.1
    mock_web_client.send_room_chat.assert_called_once()


async def test_send_calls_with_correct_args(mock_web_client):
    # Credentials set via web_client.set_session() before calling send()
    replier = Replier(web_client=mock_web_client, delay_min=0, delay_max=0)
    await replier.send("test reply")
    mock_web_client.send_room_chat.assert_called_once_with(content="test reply")


async def test_send_propagates_errors(mock_web_client):
    mock_web_client.send_room_chat = AsyncMock(side_effect=ValueError("Room ID required"))
    replier = Replier(web_client=mock_web_client, delay_min=0, delay_max=0)
    with pytest.raises(ValueError, match="Room ID"):
        await replier.send("hi")
