import logging
from enum import Enum
from typing import Callable

from TikTokLive.client.client import TikTokLiveClient
from TikTokLive.events.custom_events import DisconnectEvent, LiveEndEvent
from TikTokLive.events.proto_events import CommentEvent

logger = logging.getLogger(__name__)

CommentHandler = Callable[[str, str], None]   # (user_unique_id, comment_text)
DisconnectHandler = Callable[[], None]


class ListenerEvent(str, Enum):
    COMMENT = "comment"
    CONNECT = "connect"
    DISCONNECT = "disconnect"


class LiveListener:
    """
    Wraps TikTokLiveClient and exposes a simple callback interface.
    The TikTokLive library is NEVER modified — only used via its public API.
    """

    def __init__(self, client: TikTokLiveClient) -> None:
        self._client = client
        self._comment_handlers: list[CommentHandler] = []
        self._disconnect_handlers: list[DisconnectHandler] = []
        self._register_events()

    def _register_events(self) -> None:
        @self._client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            await self._handle_comment_event(event)

        @self._client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent):
            await self._handle_disconnect_event(event)

        @self._client.on(LiveEndEvent)
        async def on_live_end(event: LiveEndEvent):
            logger.info("LiveEndEvent received — treating as disconnect")
            await self._handle_disconnect_event(event)

    async def _handle_comment_event(self, event) -> None:
        # Use user_info (not deprecated .user property)
        user = event.user_info.unique_id if event.user_info else "unknown"
        text = event.comment or ""
        logger.debug("Comment from %s: %s", user, text[:80])
        for handler in self._comment_handlers:
            try:
                handler(user, text)
            except Exception:
                logger.exception("Comment handler error")

    async def _handle_disconnect_event(self, event) -> None:
        logger.info("Disconnect event received")
        for handler in self._disconnect_handlers:
            try:
                handler()
            except Exception:
                logger.exception("Disconnect handler error")

    def on_comment(self, handler: CommentHandler) -> None:
        self._comment_handlers.append(handler)

    def on_disconnect(self, handler: DisconnectHandler) -> None:
        self._disconnect_handlers.append(handler)

    async def start(self) -> None:
        """Non-blocking: start connection in background."""
        await self._client.start()

    async def stop(self) -> None:
        await self._client.disconnect()
