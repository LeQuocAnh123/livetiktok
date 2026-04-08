import asyncio
import logging
import random
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TikTokReplyError(Exception):
    """Raised when TikTok API rejects a chat reply."""

    def __init__(self, status_code: int, message: str, response: dict | None = None):
        self.status_code = status_code
        self.message = message
        self.response = response
        super().__init__(f"TikTok reply failed (status_code={status_code}): {message}")


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
        """Send a chat message with throttle delay. Raises TikTokReplyError on API failure."""
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.info("Throttle: waiting %.1fs before reply", delay)
        await asyncio.sleep(delay)

        # session_id + tt_target_idc already set via web_client.set_session()
        result = await self.web_client.send_room_chat(content=content)
        logger.info("Reply sent: %s | TikTok response: %s", content[:50], result)

        # Check for TikTok API errors in response
        status_code = result.get("status_code") if isinstance(result, dict) else None
        if status_code is not None and status_code != 0:
            error_msg = (
                result.get("data", {}).get("message", "Unknown error")
                if isinstance(result, dict)
                else str(result)
            )
            logger.error(
                "TikTok reply FAILED (status_code=%s): %s | content: %s",
                status_code,
                error_msg,
                content[:80],
            )
            raise TikTokReplyError(status_code=status_code, message=error_msg, response=result)

        return result
