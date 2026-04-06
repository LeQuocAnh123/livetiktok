"""Tests for RAG pipeline — all external deps mocked."""
from unittest.mock import AsyncMock

import pytest

DEFAULT_SETTINGS = {
    "tone": "friendly",
    "blacklist_keywords": ["cấm"],
    "reply_delay_min": 0,
    "reply_delay_max": 0,
    "user_cooldown_seconds": 60,
    "max_replies_per_session": 500,
    "auto_reply_enabled": True,
}

SELLER_ID = "seller-001"


def make_pipeline(embed_result=None, query_result=None, reply_result="Dạ shop còn hàng ạ!"):
    from app.core.rag.pipeline import RAGPipeline

    mock_embed = AsyncMock(return_value=embed_result or [0.1] * 1536)
    mock_retriever = AsyncMock(return_value=query_result or [
        {"id": "chunk-1", "content": "Áo cotton giá 150k", "metadata": {}, "distance": 0.1},
    ])
    mock_ai = AsyncMock(return_value=reply_result)

    return RAGPipeline(
        seller_id=SELLER_ID,
        seller_settings=DEFAULT_SETTINGS,
        embed_fn=mock_embed,
        retrieve_fn=mock_retriever,
        generate_reply_fn=mock_ai,
    ), mock_embed, mock_retriever, mock_ai


@pytest.mark.asyncio
async def test_pipeline_returns_reply_on_product_inquiry():
    """Normal comment: embed → retrieve → generate → return reply."""
    pipeline, mock_embed, mock_retriever, mock_ai = make_pipeline()
    result = await pipeline.process("user1", "Giá bao nhiêu?")

    assert result.skipped is False
    assert result.reply == "Dạ shop còn hàng ạ!"
    assert result.intent == "product_inquiry"
    assert "chunk-1" in result.chunks_used
    mock_embed.assert_called_once_with("Giá bao nhiêu?")
    mock_retriever.assert_called_once()
    mock_ai.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_skips_blacklisted_comment():
    """Blacklisted comment: skip immediately, no embed/retrieve/reply."""
    pipeline, mock_embed, mock_retriever, mock_ai = make_pipeline()
    result = await pipeline.process("user1", "spam cấm này")

    assert result.skipped is True
    assert result.intent == "skipped"
    assert result.reply is None
    mock_embed.assert_not_called()
    mock_retriever.assert_not_called()
    mock_ai.assert_not_called()


@pytest.mark.asyncio
async def test_pipeline_skips_duplicate_user_within_cooldown():
    """Second comment from same user within cooldown window is skipped."""
    pipeline, _, _, _ = make_pipeline()
    await pipeline.process("user1", "Còn hàng không?")  # first — allowed

    pipeline2, mock_embed2, _, mock_ai2 = make_pipeline()
    # Transfer cooldown state
    pipeline2._filter._cooldown_map = pipeline._filter._cooldown_map
    result = await pipeline2.process("user1", "Ship đi tỉnh không?")  # second — blocked

    assert result.skipped is True
    assert result.skip_reason == "cooldown"


@pytest.mark.asyncio
async def test_pipeline_includes_system_prompt_tone():
    """System prompt passed to AI includes the seller's configured tone."""
    pipeline, _, _, mock_ai = make_pipeline()
    await pipeline.process("user1", "Giá bao nhiêu?")

    call_kwargs = mock_ai.call_args.kwargs
    assert "friendly" in call_kwargs.get("system", "")


@pytest.mark.asyncio
async def test_pipeline_empty_retriever_still_replies():
    """When no chunks are found, AI is still called (with empty context)."""
    # Explicitly pass empty list as query_result
    from app.core.rag.pipeline import RAGPipeline

    mock_embed = AsyncMock(return_value=[0.1] * 1536)
    mock_retriever = AsyncMock(return_value=[])  # Empty result
    mock_ai = AsyncMock(return_value="Để em hỏi lại nhé ạ!")

    pipeline = RAGPipeline(
        seller_id=SELLER_ID,
        seller_settings=DEFAULT_SETTINGS,
        embed_fn=mock_embed,
        retrieve_fn=mock_retriever,
        generate_reply_fn=mock_ai,
    )
    result = await pipeline.process("user1", "Còn hàng không?")

    assert result.skipped is False
    assert result.chunks_used == []
    mock_ai.assert_called_once()
    call_kwargs = mock_ai.call_args.kwargs
    assert call_kwargs["context"] == ""
