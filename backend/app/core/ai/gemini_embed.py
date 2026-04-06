"""Google Gemini embedding implementation of EmbedProvider."""
import asyncio
import logging

from google import genai

logger = logging.getLogger(__name__)

MODEL = "gemini-embedding-001"


class GeminiEmbedProvider:
    """Uses Google Gemini text-embedding-001 (3072 dims)."""

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    async def embed(self, text: str) -> list[float]:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._client.models.embed_content(model=MODEL, contents=text),
        )
        return list(result.embeddings[0].values)
