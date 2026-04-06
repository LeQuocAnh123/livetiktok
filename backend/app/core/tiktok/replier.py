import asyncio
import logging
import random
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Replier:
    """
    Wraps TikTokWebClient.send_room_chat with random throttle delay.

    Usage:
        replier = Replier(web_client=tiktok_client.web, delay_min=5, delay_max=15)
        # Set credentials BEFORE calling send():
        tiktok_client.web.set_session(session_id, tt_target_idc)
        await replier.send("Hello!")
    """

    web_client: object  # TikTokWebClient — accessed via tiktok_client.web
    delay_min: float = 5.0
    delay_max: float = 15.0

    async def send(self, content: str) -> dict:
        """Send a chat message with throttle delay. Raises on failure."""
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.debug("Throttle: waiting %.1fs before reply", delay)
        await asyncio.sleep(delay)

        # session_id + tt_target_idc already set via web_client.set_session()
        result = await self.web_client.send_room_chat(content=content)
        logger.info("Reply sent: %s", content[:50])
        return result
