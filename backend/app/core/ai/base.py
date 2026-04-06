"""AI Provider Protocol definitions — no concrete implementations here."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class AIProvider(Protocol):
    """Protocol for LLM reply generation."""

    async def generate_reply(self, system: str, context: str, user_msg: str) -> str:
        """Generate a reply given system prompt, retrieved context, and user message."""
        ...


@runtime_checkable
class EmbedProvider(Protocol):
    """Protocol for text embedding."""

    async def embed(self, text: str) -> list[float]:
        """Return embedding vector for given text."""
        ...
