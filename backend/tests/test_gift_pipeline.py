"""Tests for RAGPipeline.process_gift() method."""

import pytest
from unittest.mock import AsyncMock

from app.core.ai.base import LLMResult
from app.core.rag.pipeline import RAGPipeline, GiftReplyResult


@pytest.fixture
def mock_pipeline():
    """RAGPipeline with all dependencies mocked."""
    return RAGPipeline(
        seller_id="seller-1",
        seller_settings={"tone": "vui ve", "auto_reply_enabled": True},
        embed_fn=AsyncMock(return_value=[0.1] * 384),
        retrieve_fn=AsyncMock(return_value=[]),
        generate_reply_fn=AsyncMock(
            return_value=LLMResult(
                intent="gift_thank",
                sentiment="positive",
                reply="Cam on ban da tang qua!",
            )
        ),
        fetch_overrides_fn=AsyncMock(return_value=[]),
    )


@pytest.mark.asyncio
async def test_process_gift_returns_gift_reply_result(mock_pipeline):
    """process_gift returns a GiftReplyResult with reply and sentiment."""
    result = await mock_pipeline.process_gift(
        user_id="viewer1",
        gift_context="Viewer viewer1 vua tang 5x Rose (5 diamonds, ~$0.03)",
    )

    assert isinstance(result, GiftReplyResult)
    assert result.reply == "Cam on ban da tang qua!"
    assert result.sentiment == "positive"


@pytest.mark.asyncio
async def test_process_gift_calls_generate_reply_fn(mock_pipeline):
    """process_gift calls generate_reply_fn with gift system prompt."""
    await mock_pipeline.process_gift(
        user_id="viewer1",
        gift_context="Viewer viewer1 vua tang 1x Lion (500 diamonds, ~$2.50)",
    )

    mock_pipeline.generate_reply_fn.assert_called_once()
    call_kwargs = mock_pipeline.generate_reply_fn.call_args
    system = call_kwargs.kwargs.get("system")
    assert system is not None
    assert "gift" in system.lower() or "cam on" in system.lower()
    context = call_kwargs.kwargs.get("context")
    assert context == ""


@pytest.mark.asyncio
async def test_process_gift_does_not_call_embed_or_retrieve(mock_pipeline):
    """process_gift skips embedding and retrieval (no RAG for gifts)."""
    await mock_pipeline.process_gift(
        user_id="viewer1",
        gift_context="Viewer viewer1 vua tang 1x Rose (1 diamonds, ~$0.01)",
    )

    mock_pipeline.embed_fn.assert_not_called()
    mock_pipeline.retrieve_fn.assert_not_called()


@pytest.mark.asyncio
async def test_process_gift_does_not_update_cooldown(mock_pipeline):
    """process_gift does not affect per-user cooldown."""
    await mock_pipeline.process_gift(
        user_id="viewer1",
        gift_context="Viewer viewer1 vua tang 1x Rose (1 diamonds, ~$0.01)",
    )

    # User should not be in cooldown map
    assert "viewer1" not in mock_pipeline._filter._cooldown_map


@pytest.mark.asyncio
async def test_process_gift_uses_seller_tone(mock_pipeline):
    """process_gift injects seller tone into system prompt."""
    mock_pipeline.seller_settings["tone"] = "chuyen nghiep"

    await mock_pipeline.process_gift(
        user_id="viewer1",
        gift_context="test gift",
    )

    call_kwargs = mock_pipeline.generate_reply_fn.call_args
    system = call_kwargs.kwargs.get("system")
    assert system is not None
    assert "chuyen nghiep" in system
