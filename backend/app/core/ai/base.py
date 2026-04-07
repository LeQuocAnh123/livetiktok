"""AI Provider Protocol definitions — no concrete implementations here."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class LLMResult:
    """Structured output from LLM: intent classification + sentiment + reply."""

    intent: str  # "product_inquiry" | "greeting" | "complaint" | "spam" | "other"
    sentiment: str  # "positive" | "neutral" | "negative"
    reply: str


@runtime_checkable
class AIProvider(Protocol):
    """Protocol for LLM reply generation with structured output."""

    async def generate_reply(self, system: str, context: str, user_msg: str) -> LLMResult:
        """Generate a structured reply with intent, sentiment, and reply text."""
        ...


@runtime_checkable
class EmbedProvider(Protocol):
    """Protocol for text embedding."""

    async def embed(self, text: str) -> list[float]:
        """Return embedding vector for given text."""
        ...
