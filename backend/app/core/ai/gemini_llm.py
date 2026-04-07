"""Google Gemini chat implementation of AIProvider."""

import asyncio
import logging

from google import genai
from google.genai import types

from app.core.ai.base import LLMResult
from app.core.ai.parse import parse_llm_json

logger = logging.getLogger(__name__)

MODEL = "gemini-2.0-flash"

_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "intent": types.Schema(
            type=types.Type.STRING,
            enum=["product_inquiry", "greeting", "complaint", "spam", "other"],
        ),
        "sentiment": types.Schema(
            type=types.Type.STRING,
            enum=["positive", "neutral", "negative"],
        ),
        "reply": types.Schema(type=types.Type.STRING),
    },
    required=["intent", "sentiment", "reply"],
)


class GeminiLLMProvider:
    """Uses Google Gemini 2.0 Flash to generate structured replies."""

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    async def generate_reply(self, system: str, context: str, user_msg: str) -> LLMResult:
        user_content = f"Context:\n{context}\n\n---\nViewer comment: {user_msg}"
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.models.generate_content(
                model=MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=512,
                    response_mime_type="application/json",
                    response_schema=_RESPONSE_SCHEMA,
                ),
            ),
        )
        raw = response.text or ""
        logger.debug("Gemini raw reply: %s", raw[:80])
        return parse_llm_json(raw)
