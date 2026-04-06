"""Groq chat completions implementation of AIProvider."""
import logging

from groq import AsyncGroq

logger = logging.getLogger(__name__)

MODEL = "llama-3.1-8b-instant"
MAX_TOKENS = 1024


class GroqProvider:
    """Uses Groq (llama-3.1-8b-instant) to generate replies."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncGroq(api_key=api_key)

    async def generate_reply(self, system: str, context: str, user_msg: str) -> str:
        user_content = f"Context:\n{context}\n\n---\nViewer comment: {user_msg}"
        response = await self._client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        )
        reply = response.choices[0].message.content or ""
        logger.debug("Groq reply: %s", reply[:80])
        return reply
