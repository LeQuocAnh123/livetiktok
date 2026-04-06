"""Google Gemini chat implementation of AIProvider."""
import asyncio
import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MODEL = "gemini-2.0-flash"


class GeminiLLMProvider:
    """Uses Google Gemini 2.0 Flash Lite to generate replies."""

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    async def generate_reply(self, system: str, context: str, user_msg: str) -> str:
        user_content = f"Context:\n{context}\n\n---\nViewer comment: {user_msg}"
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.models.generate_content(
                model=MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=512,
                ),
            ),
        )
        reply = response.text or ""
        logger.debug("Gemini reply: %s", reply[:80])
        return reply
