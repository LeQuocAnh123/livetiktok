"""Tests for AI provider abstraction layer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.ai.base import LLMResult


async def test_claude_generate_reply_calls_anthropic():
    """ClaudeProvider.generate_reply() calls Anthropic messages.create."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Dạ còn hàng ạ!")]

    with patch("app.core.ai.claude.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        from app.core.ai.claude import ClaudeProvider

        provider = ClaudeProvider(api_key="test-key")
        result = await provider.generate_reply(
            system="You are a helpful assistant.",
            context="Sản phẩm còn 10 cái.",
            user_msg="Còn hàng không?",
        )

    assert isinstance(result, LLMResult)
    assert result.reply == "Dạ còn hàng ạ!"
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["system"] == "You are a helpful assistant."


async def test_openai_llm_generate_reply_calls_openai():
    """OpenAILLMProvider.generate_reply() calls OpenAI chat completions."""
    mock_choice = MagicMock()
    mock_choice.message.content = "Giá 200k ạ!"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("app.core.ai.openai_llm.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        from app.core.ai.openai_llm import OpenAILLMProvider

        provider = OpenAILLMProvider(api_key="test-key")
        result = await provider.generate_reply(
            system="You are a seller bot.",
            context="Áo giá 200k.",
            user_msg="Giá bao nhiêu?",
        )

    assert isinstance(result, LLMResult)
    assert result.reply == "Giá 200k ạ!"


async def test_openai_embed_returns_embedding():
    """OpenAIEmbedProvider.embed() returns a list of floats."""
    mock_data = MagicMock()
    mock_data.embedding = [0.1, 0.2, 0.3]
    mock_response = MagicMock()
    mock_response.data = [mock_data]

    with patch("app.core.ai.openai_embed.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        from app.core.ai.openai_embed import OpenAIEmbedProvider

        provider = OpenAIEmbedProvider(api_key="test-key")
        result = await provider.embed("test text")

    assert result == [0.1, 0.2, 0.3]
    call_kwargs = mock_client.embeddings.create.call_args.kwargs
    assert call_kwargs["model"] == "text-embedding-3-small"
    assert call_kwargs["input"] == "test text"


def test_factory_claude_provider(monkeypatch):
    """get_reply_provider() returns ClaudeProvider when ai_reply_provider='claude'."""
    monkeypatch.setenv("SECRET_KEY", "dGVzdC1rZXktMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM=")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("AI_REPLY_PROVIDER", "claude")

    from app.config import get_settings

    get_settings.cache_clear()

    from app.core.ai import factory
    import importlib

    importlib.reload(factory)
    from app.core.ai.claude import ClaudeProvider

    provider = factory.get_reply_provider()
    assert isinstance(provider, ClaudeProvider)

    get_settings.cache_clear()


def test_factory_openai_provider(monkeypatch):
    """get_reply_provider() returns OpenAILLMProvider when ai_reply_provider='openai'."""
    monkeypatch.setenv("SECRET_KEY", "dGVzdC1rZXktMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM=")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("AI_REPLY_PROVIDER", "openai")

    from app.config import get_settings

    get_settings.cache_clear()

    from app.core.ai import factory
    import importlib

    importlib.reload(factory)
    from app.core.ai.openai_llm import OpenAILLMProvider

    provider = factory.get_reply_provider()
    assert isinstance(provider, OpenAILLMProvider)

    get_settings.cache_clear()


def test_factory_embed_provider(monkeypatch):
    """get_embed_provider() returns OpenAIEmbedProvider when AI_EMBED_PROVIDER=openai."""
    monkeypatch.setenv("SECRET_KEY", "dGVzdC1rZXktMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM=")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("AI_EMBED_PROVIDER", "openai")

    from app.config import get_settings

    get_settings.cache_clear()

    from app.core.ai import factory
    import importlib

    importlib.reload(factory)
    from app.core.ai.openai_embed import OpenAIEmbedProvider

    provider = factory.get_embed_provider()
    assert isinstance(provider, OpenAIEmbedProvider)

    get_settings.cache_clear()

    from app.core.ai import factory
    import importlib

    importlib.reload(factory)
    from app.core.ai.openai_embed import OpenAIEmbedProvider

    provider = factory.get_embed_provider()
    assert isinstance(provider, OpenAIEmbedProvider)

    get_settings.cache_clear()


def test_factory_claude_raises_without_api_key(monkeypatch):
    """get_reply_provider() raises ValueError if ANTHROPIC_API_KEY is missing."""
    from app.config import get_settings

    get_settings.cache_clear()

    monkeypatch.setenv("SECRET_KEY", "dGVzdC1rZXktMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM=")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("AI_REPLY_PROVIDER", "claude")

    from app.core.ai import factory

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        factory.get_reply_provider()

    get_settings.cache_clear()


def test_factory_openai_raises_without_api_key(monkeypatch):
    """get_reply_provider() raises ValueError if OPENAI_API_KEY is missing when provider=openai."""
    from app.config import get_settings

    get_settings.cache_clear()

    monkeypatch.setenv("SECRET_KEY", "dGVzdC1rZXktMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM=")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("AI_REPLY_PROVIDER", "openai")

    from app.core.ai import factory

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        factory.get_reply_provider()

    get_settings.cache_clear()


def test_factory_embed_raises_without_api_key(monkeypatch):
    """get_embed_provider() raises ValueError if OPENAI_API_KEY is missing when provider=openai."""
    from app.config import get_settings

    get_settings.cache_clear()

    monkeypatch.setenv("SECRET_KEY", "dGVzdC1rZXktMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM=")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("AI_EMBED_PROVIDER", "openai")

    from app.core.ai import factory

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        factory.get_embed_provider()

    get_settings.cache_clear()

    monkeypatch.setenv("SECRET_KEY", "dGVzdC1rZXktMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM=")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    from app.core.ai import factory

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        factory.get_embed_provider()

    get_settings.cache_clear()


def test_factory_unsupported_provider_raises(monkeypatch):
    """get_reply_provider() raises ValueError for unsupported provider name."""
    from app.config import get_settings

    get_settings.cache_clear()

    monkeypatch.setenv("SECRET_KEY", "dGVzdC1rZXktMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM=")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("AI_REPLY_PROVIDER", "not-a-real-provider")

    from app.core.ai import factory

    with pytest.raises(ValueError, match="Unsupported"):
        factory.get_reply_provider()

    get_settings.cache_clear()
