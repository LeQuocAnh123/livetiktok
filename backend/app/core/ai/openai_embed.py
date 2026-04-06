"""OpenAI text-embedding-3-small implementation of EmbedProvider."""
import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

EMBED_MODEL = "text-embedding-3-small"


class OpenAIEmbedProvider:
    """Uses OpenAI text-embedding-3-small to embed text."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=EMBED_MODEL,
            input=text,
        )
        embedding = response.data[0].embedding
        logger.debug("Embedded %d chars → %d dims", len(text), len(embedding))
        return embedding
