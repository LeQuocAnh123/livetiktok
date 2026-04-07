"""Parse structured JSON from LLM responses with robust fallback."""

import json
import logging
import re

from app.core.ai.base import LLMResult

logger = logging.getLogger(__name__)

_VALID_INTENTS = {"product_inquiry", "greeting", "complaint", "spam", "other"}
_VALID_SENTIMENTS = {"positive", "neutral", "negative"}


def parse_llm_json(raw: str) -> LLMResult:
    """Parse LLM response into LLMResult.

    Tries to extract JSON from the response. If parsing fails or required
    fields are missing, returns a fallback LLMResult with the raw text as reply.
    """
    if not raw.strip():
        return LLMResult(intent="other", sentiment="neutral", reply="")

    # Try to extract JSON from markdown code blocks first
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    text_to_parse = json_match.group(1).strip() if json_match else raw.strip()

    try:
        data = json.loads(text_to_parse)
    except json.JSONDecodeError:
        # Try to find a JSON object anywhere in the text
        obj_match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        if obj_match:
            try:
                data = json.loads(obj_match.group(0))
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM JSON, using raw text as reply")
                return LLMResult(intent="other", sentiment="neutral", reply=raw.strip())
        else:
            logger.warning("No JSON found in LLM response, using raw text as reply")
            return LLMResult(intent="other", sentiment="neutral", reply=raw.strip())

    # Validate required fields
    if not isinstance(data, dict):
        return LLMResult(intent="other", sentiment="neutral", reply=raw.strip())

    intent = data.get("intent", "other")
    sentiment = data.get("sentiment", "neutral")
    reply = data.get("reply", "")

    if not all([isinstance(intent, str), isinstance(sentiment, str), isinstance(reply, str)]):
        return LLMResult(intent="other", sentiment="neutral", reply=raw.strip())

    # Validate enum values
    if intent not in _VALID_INTENTS:
        intent = "other"
    if sentiment not in _VALID_SENTIMENTS:
        sentiment = "neutral"

    return LLMResult(intent=intent, sentiment=sentiment, reply=reply)
