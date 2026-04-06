"""Factory functions to get configured AI providers from settings."""
from app.config import get_settings
from app.core.ai.base import AIProvider, EmbedProvider
from app.core.ai.claude import ClaudeProvider
from app.core.ai.openai_embed import OpenAIEmbedProvider
from app.core.ai.openai_llm import OpenAILLMProvider


def get_reply_provider() -> AIProvider:
    """Return configured reply provider based on AI_REPLY_PROVIDER setting."""
    settings = get_settings()
    provider_name = settings.ai_reply_provider.lower()

    if provider_name == "claude":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when AI_REPLY_PROVIDER=claude")
        return ClaudeProvider(api_key=settings.anthropic_api_key)

    if provider_name == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when AI_REPLY_PROVIDER=openai")
        return OpenAILLMProvider(api_key=settings.openai_api_key)

    raise ValueError(f"Unsupported AI_REPLY_PROVIDER: {provider_name!r}. Use 'claude' or 'openai'.")


def get_embed_provider() -> EmbedProvider:
    """Return configured embed provider (always OpenAI in v1)."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for embeddings")
    return OpenAIEmbedProvider(api_key=settings.openai_api_key)
