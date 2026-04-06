"""Local embedding using FastEmbed (no API key required)."""
import asyncio
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

MODEL = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def _get_model():
    from fastembed import TextEmbedding
    logger.info("Loading FastEmbed model %s (first-time download may take a moment)...", MODEL)
    return TextEmbedding(model_name=MODEL)


class FastEmbedProvider:
    """Local embeddings via FastEmbed — no API key needed."""

    async def embed(self, text: str) -> list[float]:
        loop = asyncio.get_event_loop()
        model = await loop.run_in_executor(None, _get_model)
        embeddings = await loop.run_in_executor(None, lambda: list(model.embed([text])))
        return embeddings[0].tolist()
