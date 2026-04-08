import inspect
import logging
from enum import Enum
from typing import Callable

from TikTokLive.client.client import TikTokLiveClient
from TikTokLive.events.custom_events import ConnectEvent, DisconnectEvent, LiveEndEvent
from TikTokLive.events.proto_events import CommentEvent, GiftEvent

logger = logging.getLogger(__name__)

CommentHandler = Callable[[str, str], None]  # (user_unique_id, comment_text)
GiftHandler = Callable[
    [str, str, int, int], None
]  # (user_unique_id, gift_name, diamond_count, repeat_count)
DisconnectHandler = Callable[[], None]


class ListenerEvent(str, Enum):
    COMMENT = "comment"
    GIFT = "gift"
    DISCONNECT = "disconnect"


class LiveListener:
    """
    Wraps TikTokLiveClient and exposes a simple callback interface.
    The TikTokLive library is NEVER modified — only used via its public API.
    """

    def __init__(self, client: TikTokLiveClient) -> None:
        self._client = client
        self._comment_handlers: list[CommentHandler] = []
        self._gift_handlers: list[GiftHandler] = []
        self._disconnect_handlers: list[DisconnectHandler] = []
        self._register_events()

    def _register_events(self) -> None:
        @self._client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            logger.info(
                "Connected to TikTok Live room (unique_id=%s, room_id=%s)",
                self._client.unique_id,
                self._client.room_id,
            )

        @self._client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            await self._handle_comment_event(event)

        @self._client.on(GiftEvent)
        async def on_gift(event: GiftEvent):
            await self._handle_gift_event(event)

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
        logger.info("Comment from %s: %s", user, text[:80])
        for handler in self._comment_handlers:
            try:
                result = handler(user, text)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Comment handler error")

    async def _handle_gift_event(self, event) -> None:
        """Handle incoming gift events with streak filtering.

        Only dispatches when:
        - Gift is not streakable (single gift), OR
        - Gift is streakable and streak has ended (streaking=False / repeat_end=True)
        """
        # Skip mid-streak events
        if event.gift.streakable and event.streaking:
            logger.debug("Skipping mid-streak gift from %s", event.user.unique_id)
            return

        user = event.user.unique_id
        gift_name = event.gift.name
        diamond_count = event.gift.diamond_count
        repeat_count = event.repeat_count

        logger.info(
            "Gift from %s: %dx %s (%d diamonds each)",
            user,
            repeat_count,
            gift_name,
            diamond_count,
        )

        for handler in self._gift_handlers:
            try:
                result = handler(user, gift_name, diamond_count, repeat_count)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Gift handler error")

    async def _handle_disconnect_event(self, event) -> None:
        logger.info("Disconnect event received")
        for handler in self._disconnect_handlers:
            try:
                result = handler()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Disconnect handler error")

    def on_comment(self, handler: CommentHandler) -> None:
        self._comment_handlers.append(handler)

    def on_gift(self, handler: GiftHandler) -> None:
        self._gift_handlers.append(handler)

    def on_disconnect(self, handler: DisconnectHandler) -> None:
        self._disconnect_handlers.append(handler)

    async def start(self) -> None:
        """Non-blocking: start connection in background."""
        logger.info("Starting TikTok listener for unique_id=%s ...", self._client.unique_id)
        try:
            await self._client.start()
        except Exception:
            logger.exception(
                "TikTok listener failed to start for unique_id=%s", self._client.unique_id
            )
            raise

    async def stop(self) -> None:
        await self._client.disconnect()
