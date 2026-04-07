"""OpenAI chat completions implementation of AIProvider."""

import logging

from openai import AsyncOpenAI

from app.core.ai.base import LLMResult
from app.core.ai.parse import parse_llm_json

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"
MAX_TOKENS = 1024

_JSON_SCHEMA = {
    "name": "structured_reply",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["product_inquiry", "greeting", "complaint", "spam", "other"],
            },
            "sentiment": {
                "type": "string",
                "enum": ["positive", "neutral", "negative"],
            },
            "reply": {
                "type": "string",
            },
        },
        "required": ["intent", "sentiment", "reply"],
        "additionalProperties": False,
    },
}


class OpenAILLMProvider:
    """Uses OpenAI gpt-4o-mini to generate structured replies."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

    async def generate_reply(self, system: str, context: str, user_msg: str) -> LLMResult:
        user_content = f"Context:\n{context}\n\n---\nViewer comment: {user_msg}"
        response = await self._client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_schema", "json_schema": _JSON_SCHEMA},
        )
        raw = response.choices[0].message.content or ""
        logger.debug("OpenAI raw reply: %s", raw[:80])
        return parse_llm_json(raw)
