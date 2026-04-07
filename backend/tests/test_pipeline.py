"""Tests for the updated RAG pipeline with structured LLM output and overrides."""

import pytest
from unittest.mock import AsyncMock

from app.core.ai.base import LLMResult
from app.core.rag.pipeline import RAGPipeline, RAGResult


@pytest.mark.asyncio
async def test_pipeline_returns_intent_and_sentiment():
    """Pipeline returns intent and sentiment from LLMResult."""
    pipeline = RAGPipeline(
        seller_id="s1",
        seller_settings={"tone": "friendly", "auto_reply_enabled": True, "blacklist_keywords": []},
        embed_fn=AsyncMock(return_value=[0.1] * 10),
        retrieve_fn=AsyncMock(return_value=[{"id": "c1", "content": "Áo giá 150k"}]),
        generate_reply_fn=AsyncMock(
            return_value=LLMResult(
                intent="product_inquiry", sentiment="neutral", reply="Dạ giá 150k ạ!"
            )
        ),
        fetch_overrides_fn=AsyncMock(return_value=[]),
    )

    result = await pipeline.process("user1", "Giá bao nhiêu?")

    assert not result.skipped
    assert result.intent == "product_inquiry"
    assert result.sentiment == "neutral"
    assert result.reply == "Dạ giá 150k ạ!"
    assert result.chunks_used == ["c1"]


@pytest.mark.asyncio
async def test_pipeline_injects_override_examples():
    """Pipeline passes override examples to prompt building."""
    overrides = [
        ("Giá bao nhiêu?", "Dạ 150k thôi ạ!"),
        ("Ship lâu không?", "Dạ 2-3 ngày ạ!"),
    ]
    mock_generate = AsyncMock(
        return_value=LLMResult(intent="product_inquiry", sentiment="neutral", reply="Dạ 150k ạ!")
    )
    pipeline = RAGPipeline(
        seller_id="s1",
        seller_settings={"tone": "friendly", "auto_reply_enabled": True, "blacklist_keywords": []},
        embed_fn=AsyncMock(return_value=[0.1] * 10),
        retrieve_fn=AsyncMock(return_value=[{"id": "c1", "content": "Áo giá 150k"}]),
        generate_reply_fn=mock_generate,
        fetch_overrides_fn=AsyncMock(return_value=overrides),
    )

    await pipeline.process("user1", "Giá bao nhiêu?")

    # Verify the system prompt contains override examples
    call_kwargs = mock_generate.call_args
    system_prompt = call_kwargs.kwargs.get("system") or call_kwargs.args[0]
    assert "Dạ 150k thôi ạ!" in system_prompt
    assert "Ship lâu không?" in system_prompt


@pytest.mark.asyncio
async def test_pipeline_skipped_returns_neutral_sentiment():
    """Skipped comments return neutral sentiment."""
    pipeline = RAGPipeline(
        seller_id="s1",
        seller_settings={
            "tone": "friendly",
            "auto_reply_enabled": True,
            "blacklist_keywords": ["spam"],
        },
        embed_fn=AsyncMock(),
        retrieve_fn=AsyncMock(),
        generate_reply_fn=AsyncMock(),
        fetch_overrides_fn=AsyncMock(return_value=[]),
    )

    result = await pipeline.process("user1", "This is spam content")

    assert result.skipped
    assert result.sentiment == "neutral"
    assert result.intent == "skipped"


@pytest.mark.asyncio
async def test_pipeline_no_overrides_no_examples_in_prompt():
    """When no overrides exist, prompt has no examples section."""
    mock_generate = AsyncMock(
        return_value=LLMResult(intent="greeting", sentiment="positive", reply="Chào bạn!")
    )
    pipeline = RAGPipeline(
        seller_id="s1",
        seller_settings={"tone": "friendly", "auto_reply_enabled": True, "blacklist_keywords": []},
        embed_fn=AsyncMock(return_value=[0.1] * 10),
        retrieve_fn=AsyncMock(return_value=[]),
        generate_reply_fn=mock_generate,
        fetch_overrides_fn=AsyncMock(return_value=[]),
    )

    await pipeline.process("user1", "Hello!")

    call_kwargs = mock_generate.call_args
    system_prompt = call_kwargs.kwargs.get("system") or call_kwargs.args[0]
    assert "Hãy học theo phong cách này" not in system_prompt
