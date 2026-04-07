"""Tests for LLMResult dataclass."""

from app.core.ai.base import LLMResult


def test_llm_result_creation():
    result = LLMResult(intent="product_inquiry", sentiment="neutral", reply="Dạ giá 150k ạ!")
    assert result.intent == "product_inquiry"
    assert result.sentiment == "neutral"
    assert result.reply == "Dạ giá 150k ạ!"


def test_llm_result_fields_are_strings():
    result = LLMResult(intent="greeting", sentiment="positive", reply="Chào bạn!")
    assert isinstance(result.intent, str)
    assert isinstance(result.sentiment, str)
    assert isinstance(result.reply, str)
