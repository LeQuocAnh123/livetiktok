"""Tests for structured output from all AI providers."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.ai.base import LLMResult


@pytest.mark.asyncio
async def test_claude_returns_llm_result():
    """Claude provider parses tool_use response into LLMResult."""
    from app.core.ai.claude import ClaudeProvider

    mock_client = AsyncMock()
    provider = ClaudeProvider.__new__(ClaudeProvider)
    provider._client = mock_client

    # Simulate Claude tool_use response
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "structured_reply"
    tool_block.input = {
        "intent": "product_inquiry",
        "sentiment": "neutral",
        "reply": "Dạ giá 150k ạ!",
    }
    mock_response = MagicMock()
    mock_response.content = [tool_block]
    mock_response.stop_reason = "tool_use"
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    result = await provider.generate_reply(
        system="test system", context="test context", user_msg="Giá bao nhiêu?"
    )

    assert isinstance(result, LLMResult)
    assert result.intent == "product_inquiry"
    assert result.sentiment == "neutral"
    assert result.reply == "Dạ giá 150k ạ!"


@pytest.mark.asyncio
async def test_claude_fallback_on_text_response():
    """Claude provider falls back to parse.py when response is text (no tool_use)."""
    from app.core.ai.claude import ClaudeProvider

    mock_client = AsyncMock()
    provider = ClaudeProvider.__new__(ClaudeProvider)
    provider._client = mock_client

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = '{"intent": "greeting", "sentiment": "positive", "reply": "Chào bạn!"}'
    mock_response = MagicMock()
    mock_response.content = [text_block]
    mock_response.stop_reason = "end_turn"
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    result = await provider.generate_reply(system="test", context="ctx", user_msg="Hello")

    assert isinstance(result, LLMResult)
    assert result.intent == "greeting"
    assert result.reply == "Chào bạn!"


@pytest.mark.asyncio
async def test_openai_returns_llm_result():
    """OpenAI provider parses json_schema response into LLMResult."""
    from app.core.ai.openai_llm import OpenAILLMProvider

    mock_client = AsyncMock()
    provider = OpenAILLMProvider.__new__(OpenAILLMProvider)
    provider._client = mock_client

    mock_message = MagicMock()
    mock_message.content = json.dumps(
        {
            "intent": "complaint",
            "sentiment": "negative",
            "reply": "Dạ em xin lỗi ạ!",
        }
    )
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await provider.generate_reply(
        system="test", context="ctx", user_msg="Giao hàng chậm quá!"
    )

    assert isinstance(result, LLMResult)
    assert result.intent == "complaint"
    assert result.sentiment == "negative"
    assert result.reply == "Dạ em xin lỗi ạ!"


@pytest.mark.asyncio
async def test_openai_fallback_on_plain_text():
    """OpenAI provider falls back when response is not JSON."""
    from app.core.ai.openai_llm import OpenAILLMProvider

    mock_client = AsyncMock()
    provider = OpenAILLMProvider.__new__(OpenAILLMProvider)
    provider._client = mock_client

    mock_message = MagicMock()
    mock_message.content = "Dạ giá 150k ạ!"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await provider.generate_reply(system="test", context="ctx", user_msg="Giá?")

    assert isinstance(result, LLMResult)
    assert result.intent == "other"
    assert result.sentiment == "neutral"
    assert result.reply == "Dạ giá 150k ạ!"


@pytest.mark.asyncio
async def test_groq_returns_llm_result():
    """Groq provider parses json_object response into LLMResult."""
    from app.core.ai.groq_llm import GroqProvider

    mock_client = AsyncMock()
    provider = GroqProvider.__new__(GroqProvider)
    provider._client = mock_client

    mock_message = MagicMock()
    mock_message.content = json.dumps(
        {
            "intent": "greeting",
            "sentiment": "positive",
            "reply": "Chào bạn! Cảm ơn đã ghé shop!",
        }
    )
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await provider.generate_reply(system="test", context="ctx", user_msg="Hello shop!")

    assert isinstance(result, LLMResult)
    assert result.intent == "greeting"
    assert result.sentiment == "positive"
    assert result.reply == "Chào bạn! Cảm ơn đã ghé shop!"


@pytest.mark.asyncio
async def test_gemini_returns_llm_result():
    """Gemini provider parses structured response into LLMResult."""
    from app.core.ai.gemini_llm import GeminiLLMProvider

    mock_client = MagicMock()
    provider = GeminiLLMProvider.__new__(GeminiLLMProvider)
    provider._client = mock_client

    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "intent": "spam",
            "sentiment": "neutral",
            "reply": "Dạ bên em chuyên về thời trang, bên em không hỗ trợ vấn đề này ạ!",
        }
    )
    mock_client.models.generate_content = MagicMock(return_value=mock_response)

    with patch("app.core.ai.gemini_llm.asyncio") as mock_asyncio:
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_response)
        mock_asyncio.get_event_loop.return_value = mock_loop

        result = await provider.generate_reply(
            system="test", context="ctx", user_msg="Bán acc game không?"
        )

    assert isinstance(result, LLMResult)
    assert result.intent == "spam"
    assert result.reply == "Dạ bên em chuyên về thời trang, bên em không hỗ trợ vấn đề này ạ!"
