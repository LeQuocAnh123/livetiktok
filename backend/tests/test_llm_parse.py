"""Tests for LLM JSON response parsing."""

from app.core.ai.parse import parse_llm_json
from app.core.ai.base import LLMResult


def test_parse_valid_json():
    raw = '{"intent": "product_inquiry", "sentiment": "neutral", "reply": "Dạ giá 150k ạ!"}'
    result = parse_llm_json(raw)
    assert result.intent == "product_inquiry"
    assert result.sentiment == "neutral"
    assert result.reply == "Dạ giá 150k ạ!"


def test_parse_json_with_extra_fields():
    raw = '{"intent": "greeting", "sentiment": "positive", "reply": "Chào bạn!", "extra": 123}'
    result = parse_llm_json(raw)
    assert result.intent == "greeting"
    assert result.reply == "Chào bạn!"


def test_parse_json_embedded_in_markdown():
    raw = 'Here is the response:\n```json\n{"intent": "other", "sentiment": "neutral", "reply": "Dạ bên em không hỗ trợ ạ!"}\n```'
    result = parse_llm_json(raw)
    assert result.intent == "other"
    assert result.reply == "Dạ bên em không hỗ trợ ạ!"


def test_parse_invalid_json_returns_fallback():
    raw = "Dạ giá 150k ạ!"
    result = parse_llm_json(raw)
    assert result.intent == "other"
    assert result.sentiment == "neutral"
    assert result.reply == "Dạ giá 150k ạ!"


def test_parse_json_missing_fields_returns_fallback():
    raw = '{"reply": "Dạ giá 150k ạ!"}'
    result = parse_llm_json(raw)
    assert result.intent == "other"
    assert result.sentiment == "neutral"
    assert result.reply == "Dạ giá 150k ạ!"


def test_parse_empty_string_returns_fallback():
    result = parse_llm_json("")
    assert result.intent == "other"
    assert result.sentiment == "neutral"
    assert result.reply == ""
