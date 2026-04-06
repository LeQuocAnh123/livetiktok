"""Factory functions to get configured AI providers from settings."""
from app.config import get_settings
from app.core.ai.base import AIProvider, EmbedProvider
from app.core.ai.claude import ClaudeProvider
from app.core.ai.fastembed_embed import FastEmbedProvider
from app.core.ai.gemini_embed import GeminiEmbedProvider
from app.core.ai.gemini_llm import GeminiLLMProvider
from app.core.ai.groq_llm import GroqProvider
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

    if provider_name == "groq":
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when AI_REPLY_PROVIDER=groq")
        return GroqProvider(api_key=settings.groq_api_key)

    if provider_name == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when AI_REPLY_PROVIDER=gemini")
        return GeminiLLMProvider(api_key=settings.gemini_api_key)

    raise ValueError(f"Unsupported AI_REPLY_PROVIDER: {provider_name!r}. Use 'claude', 'openai', 'groq', or 'gemini'.")


def get_embed_provider() -> EmbedProvider:
    """Return configured embed provider based on AI_EMBED_PROVIDER setting."""
    settings = get_settings()
    provider_name = settings.ai_embed_provider.lower()

    if provider_name == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when AI_EMBED_PROVIDER=openai")
        return OpenAIEmbedProvider(api_key=settings.openai_api_key)

    if provider_name == "fastembed":
        return FastEmbedProvider()

    if provider_name == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when AI_EMBED_PROVIDER=gemini")
        return GeminiEmbedProvider(api_key=settings.gemini_api_key)

    raise ValueError(f"Unsupported AI_EMBED_PROVIDER: {provider_name!r}. Use 'openai', 'fastembed', or 'gemini'.")
