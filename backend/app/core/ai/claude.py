"""Anthropic Claude implementation of AIProvider."""
import logging

from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024


class ClaudeProvider:
    """Uses Anthropic claude-sonnet-4-6 to generate replies."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    async def generate_reply(self, system: str, context: str, user_msg: str) -> str:
        user_content = f"Context:\n{context}\n\n---\nViewer comment: {user_msg}"
        message = await self._client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        reply = message.content[0].text
        logger.debug("Claude reply: %s", reply[:80])
        return reply
