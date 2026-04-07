"""Anthropic Claude implementation of AIProvider."""

import logging

from anthropic import AsyncAnthropic

from app.core.ai.base import LLMResult
from app.core.ai.parse import parse_llm_json

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

_STRUCTURED_TOOL = {
    "name": "structured_reply",
    "description": "Return the structured reply with intent, sentiment, and reply text.",
    "input_schema": {
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
                "description": "The reply text in Vietnamese",
            },
        },
        "required": ["intent", "sentiment", "reply"],
    },
}


class ClaudeProvider:
    """Uses Anthropic claude-sonnet-4-6 to generate structured replies."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    async def generate_reply(self, system: str, context: str, user_msg: str) -> LLMResult:
        user_content = f"Context:\n{context}\n\n---\nViewer comment: {user_msg}"
        message = await self._client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_content}],
            tools=[_STRUCTURED_TOOL],
            tool_choice={"type": "tool", "name": "structured_reply"},
        )

        # Extract from tool_use block
        for block in message.content:
            if block.type == "tool_use" and block.name == "structured_reply":
                data = block.input
                logger.debug("Claude structured reply: %s", str(data)[:80])
                return LLMResult(
                    intent=data.get("intent", "other"),
                    sentiment=data.get("sentiment", "neutral"),
                    reply=data.get("reply", ""),
                )

        # Fallback: parse text response
        raw = message.content[0].text if message.content else ""
        logger.warning("Claude did not use tool, falling back to JSON parse")
        return parse_llm_json(raw)
