# LLM-Based Classification, Sentiment Analysis & Learning from Overrides — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace keyword-based intent detection with LLM classification, add sentiment analysis, and learn from seller manual overrides via few-shot prompt injection — all in a single LLM call.

**Architecture:** Unified structured-output LLM call returns `{intent, sentiment, reply}` JSON. Each AI provider uses its native structured output mechanism with a universal JSON fallback. Recent manual override examples are fetched from `MessageLog` and injected into the system prompt as few-shot examples. Negative sentiment comments bypass cooldown and trigger dashboard alerts.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Anthropic/OpenAI/Groq/Gemini SDKs, pytest + pytest-asyncio

---

### Task 1: Add `LLMResult` Dataclass and Update `AIProvider` Protocol

**Files:**
- Modify: `backend/app/core/ai/base.py`
- Test: `backend/tests/test_llm_result.py`

- [ ] **Step 1: Write test for LLMResult dataclass**

Create `backend/tests/test_llm_result.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_llm_result.py -v`
Expected: FAIL with `ImportError: cannot import name 'LLMResult'`

- [ ] **Step 3: Implement LLMResult and update AIProvider protocol**

Replace the entire content of `backend/app/core/ai/base.py` with:

```python
"""AI Provider Protocol definitions — no concrete implementations here."""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class LLMResult:
    """Structured output from LLM: intent classification + sentiment + reply."""

    intent: str  # "product_inquiry" | "greeting" | "complaint" | "spam" | "other"
    sentiment: str  # "positive" | "neutral" | "negative"
    reply: str


@runtime_checkable
class AIProvider(Protocol):
    """Protocol for LLM reply generation with structured output."""

    async def generate_reply(self, system: str, context: str, user_msg: str) -> LLMResult:
        """Generate a structured reply with intent, sentiment, and reply text."""
        ...


@runtime_checkable
class EmbedProvider(Protocol):
    """Protocol for text embedding."""

    async def embed(self, text: str) -> list[float]:
        """Return embedding vector for given text."""
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_llm_result.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/ai/base.py backend/tests/test_llm_result.py
git commit -m "feat: add LLMResult dataclass and update AIProvider protocol for structured output"
```

---

### Task 2: Add JSON Parsing Helper

**Files:**
- Create: `backend/app/core/ai/parse.py`
- Test: `backend/tests/test_llm_parse.py`

- [ ] **Step 1: Write tests for JSON parsing helper**

Create `backend/tests/test_llm_parse.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_llm_parse.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.ai.parse'`

- [ ] **Step 3: Implement parse_llm_json**

Create `backend/app/core/ai/parse.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_llm_parse.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/ai/parse.py backend/tests/test_llm_parse.py
git commit -m "feat: add JSON parsing helper for structured LLM output with robust fallback"
```

---

### Task 3: Update Claude Provider for Structured Output

**Files:**
- Modify: `backend/app/core/ai/claude.py`
- Test: `backend/tests/test_llm_structured_output.py`

- [ ] **Step 1: Write test for Claude provider structured output**

Create `backend/tests/test_llm_structured_output.py`:

```python
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

    result = await provider.generate_reply(
        system="test", context="ctx", user_msg="Hello"
    )

    assert isinstance(result, LLMResult)
    assert result.intent == "greeting"
    assert result.reply == "Chào bạn!"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_llm_structured_output.py::test_claude_returns_llm_result -v`
Expected: FAIL — `generate_reply` returns `str`, not `LLMResult`

- [ ] **Step 3: Update Claude provider**

Replace `backend/app/core/ai/claude.py` with:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_llm_structured_output.py -k claude -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/ai/claude.py backend/tests/test_llm_structured_output.py
git commit -m "feat: update Claude provider for structured output returning LLMResult"
```

---

### Task 4: Update OpenAI Provider for Structured Output

**Files:**
- Modify: `backend/app/core/ai/openai_llm.py`
- Modify: `backend/tests/test_llm_structured_output.py`

- [ ] **Step 1: Add test for OpenAI provider**

Append to `backend/tests/test_llm_structured_output.py`:

```python
@pytest.mark.asyncio
async def test_openai_returns_llm_result():
    """OpenAI provider parses json_schema response into LLMResult."""
    from app.core.ai.openai_llm import OpenAILLMProvider

    mock_client = AsyncMock()
    provider = OpenAILLMProvider.__new__(OpenAILLMProvider)
    provider._client = mock_client

    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "intent": "complaint",
        "sentiment": "negative",
        "reply": "Dạ em xin lỗi ạ!",
    })
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

    result = await provider.generate_reply(
        system="test", context="ctx", user_msg="Giá?"
    )

    assert isinstance(result, LLMResult)
    assert result.intent == "other"
    assert result.sentiment == "neutral"
    assert result.reply == "Dạ giá 150k ạ!"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_llm_structured_output.py::test_openai_returns_llm_result -v`
Expected: FAIL — `generate_reply` returns `str`

- [ ] **Step 3: Update OpenAI provider**

Replace `backend/app/core/ai/openai_llm.py` with:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_llm_structured_output.py -k openai -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/ai/openai_llm.py backend/tests/test_llm_structured_output.py
git commit -m "feat: update OpenAI provider for structured output returning LLMResult"
```

---

### Task 5: Update Groq Provider for Structured Output

**Files:**
- Modify: `backend/app/core/ai/groq_llm.py`
- Modify: `backend/tests/test_llm_structured_output.py`

- [ ] **Step 1: Add test for Groq provider**

Append to `backend/tests/test_llm_structured_output.py`:

```python
@pytest.mark.asyncio
async def test_groq_returns_llm_result():
    """Groq provider parses json_object response into LLMResult."""
    from app.core.ai.groq_llm import GroqProvider

    mock_client = AsyncMock()
    provider = GroqProvider.__new__(GroqProvider)
    provider._client = mock_client

    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "intent": "greeting",
        "sentiment": "positive",
        "reply": "Chào bạn! Cảm ơn đã ghé shop!",
    })
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await provider.generate_reply(
        system="test", context="ctx", user_msg="Hello shop!"
    )

    assert isinstance(result, LLMResult)
    assert result.intent == "greeting"
    assert result.sentiment == "positive"
    assert result.reply == "Chào bạn! Cảm ơn đã ghé shop!"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_llm_structured_output.py::test_groq_returns_llm_result -v`
Expected: FAIL — `generate_reply` returns `str`

- [ ] **Step 3: Update Groq provider**

Replace `backend/app/core/ai/groq_llm.py` with:

```python
"""Groq chat completions implementation of AIProvider."""
import logging

from groq import AsyncGroq

from app.core.ai.base import LLMResult
from app.core.ai.parse import parse_llm_json

logger = logging.getLogger(__name__)

MODEL = "llama-3.1-8b-instant"
MAX_TOKENS = 1024


class GroqProvider:
    """Uses Groq (llama-3.1-8b-instant) to generate structured replies."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncGroq(api_key=api_key)

    async def generate_reply(self, system: str, context: str, user_msg: str) -> LLMResult:
        user_content = f"Context:\n{context}\n\n---\nViewer comment: {user_msg}"
        response = await self._client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
        logger.debug("Groq raw reply: %s", raw[:80])
        return parse_llm_json(raw)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_llm_structured_output.py::test_groq_returns_llm_result -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/ai/groq_llm.py backend/tests/test_llm_structured_output.py
git commit -m "feat: update Groq provider for structured output returning LLMResult"
```

---

### Task 6: Update Gemini Provider for Structured Output

**Files:**
- Modify: `backend/app/core/ai/gemini_llm.py`
- Modify: `backend/tests/test_llm_structured_output.py`

- [ ] **Step 1: Add test for Gemini provider**

Append to `backend/tests/test_llm_structured_output.py`:

```python
@pytest.mark.asyncio
async def test_gemini_returns_llm_result():
    """Gemini provider parses structured response into LLMResult."""
    from app.core.ai.gemini_llm import GeminiLLMProvider

    mock_client = MagicMock()
    provider = GeminiLLMProvider.__new__(GeminiLLMProvider)
    provider._client = mock_client

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "intent": "spam",
        "sentiment": "neutral",
        "reply": "Dạ bên em chuyên về thời trang, bên em không hỗ trợ vấn đề này ạ!",
    })
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_llm_structured_output.py::test_gemini_returns_llm_result -v`
Expected: FAIL — `generate_reply` returns `str`

- [ ] **Step 3: Update Gemini provider**

Replace `backend/app/core/ai/gemini_llm.py` with:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_llm_structured_output.py::test_gemini_returns_llm_result -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/ai/gemini_llm.py backend/tests/test_llm_structured_output.py
git commit -m "feat: update Gemini provider for structured output returning LLMResult"
```

---

### Task 7: Add `sentiment` Column to MessageLog + Alembic Migration

**Files:**
- Modify: `backend/app/models/message.py`
- Create: `backend/alembic/versions/xxxx_add_sentiment_to_message_logs.py`
- Test: `backend/tests/test_message_model.py`

- [ ] **Step 1: Write test for sentiment column**

Create `backend/tests/test_message_model.py`:

```python
"""Tests for MessageLog model with sentiment field."""
import pytest

from app.models.message import MessageLog
from app.models.session import LiveSession, SessionStatus


@pytest.mark.asyncio
async def test_message_log_default_sentiment(db_session, test_seller):
    """MessageLog defaults sentiment to 'neutral'."""
    session = LiveSession(seller_id=test_seller.id, status=SessionStatus.ACTIVE)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    msg = MessageLog(
        session_id=session.id,
        user_unique_id="viewer1",
        comment="Hello",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)

    assert msg.sentiment == "neutral"


@pytest.mark.asyncio
async def test_message_log_explicit_sentiment(db_session, test_seller):
    """MessageLog stores explicit sentiment value."""
    session = LiveSession(seller_id=test_seller.id, status=SessionStatus.ACTIVE)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    msg = MessageLog(
        session_id=session.id,
        user_unique_id="viewer2",
        comment="Giao hàng chậm quá!",
        sentiment="negative",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)

    assert msg.sentiment == "negative"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_message_model.py -v`
Expected: FAIL — `MessageLog` has no `sentiment` attribute

- [ ] **Step 3: Add sentiment column to MessageLog**

In `backend/app/models/message.py`, add the `sentiment` column after the `intent` column (after line 22):

```python
    sentiment: Mapped[str] = mapped_column(String, nullable=False, default="neutral")
```

The full updated file:

```python
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.session import LiveSession


class MessageLog(Base):
    __tablename__ = "message_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("live_sessions.id"), nullable=False)
    user_unique_id: Mapped[str] = mapped_column(String, nullable=False)
    comment: Mapped[str] = mapped_column(String, nullable=False)
    reply: Mapped[str | None] = mapped_column(String, nullable=True)
    intent: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    sentiment: Mapped[str] = mapped_column(String, nullable=False, default="neutral")
    chunks_used: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["LiveSession"] = relationship(back_populates="messages")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_message_model.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Generate Alembic migration**

Run: `python3 -m alembic revision --autogenerate -m "add sentiment to message_logs"`

Verify the generated migration adds the `sentiment` column with server default `"neutral"`. Edit if needed to ensure:

```python
op.add_column('message_logs', sa.Column('sentiment', sa.String(), nullable=False, server_default='neutral'))
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/message.py backend/alembic/versions/*_add_sentiment_to_message_logs.py backend/tests/test_message_model.py
git commit -m "feat: add sentiment column to MessageLog model with Alembic migration"
```

---

### Task 8: Update RAGPipeline for Structured Output + Override Fetching

**Files:**
- Modify: `backend/app/core/rag/pipeline.py`
- Modify: `backend/app/core/rag/filter.py`
- Test: `backend/tests/test_pipeline.py`

- [ ] **Step 1: Write tests for updated pipeline**

Create `backend/tests/test_pipeline.py`:

```python
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
            return_value=LLMResult(intent="product_inquiry", sentiment="neutral", reply="Dạ giá 150k ạ!")
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `RAGPipeline` does not accept `fetch_overrides_fn`, `RAGResult` has no `sentiment`

- [ ] **Step 3: Add `reset_cooldown` to CommentFilter**

In `backend/app/core/rag/filter.py`, add after line 69 (after `update_cooldown`):

```python
    def reset_cooldown(self, user_id: str) -> None:
        """Remove user from cooldown map (e.g. for negative sentiment priority)."""
        self._cooldown_map.pop(user_id, None)
```

Also remove `detect_intent` and `_INTENT_KEYWORDS` (lines 9-29) since the LLM now handles classification. Update the import line and docstring accordingly.

Full updated `backend/app/core/rag/filter.py`:

```python
"""Comment filter: blacklist keywords, per-user cooldown."""
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    skip: bool
    reason: str | None = None  # "blacklist" | "cooldown" | "auto_reply_disabled" | None


@dataclass
class CommentFilter:
    """Stateful filter — holds per-user cooldown timestamps for a session."""

    _settings: dict[str, Any]
    _cooldown_map: dict[str, float] = field(default_factory=dict)

    def check(self, user_id: str, text: str) -> FilterResult:
        """Return FilterResult(skip=True, reason=...) if comment should be skipped."""
        # 1. auto_reply_enabled gate
        if not self._settings.get("auto_reply_enabled", True):
            return FilterResult(skip=True, reason="auto_reply_disabled")

        # 2. Blacklist
        blacklist = self._settings.get("blacklist_keywords", [])
        text_lower = text.lower()
        if any(kw.lower() in text_lower for kw in blacklist):
            logger.debug("Blacklist hit for user %s: %s", user_id, text[:40])
            return FilterResult(skip=True, reason="blacklist")

        # 3. Per-user cooldown
        cooldown_secs = self._settings.get("user_cooldown_seconds", 60)
        last_reply = self._cooldown_map.get(user_id)
        if last_reply is not None and (time.time() - last_reply) < cooldown_secs:
            logger.debug("Cooldown hit for user %s", user_id)
            return FilterResult(skip=True, reason="cooldown")

        return FilterResult(skip=False)

    def update_cooldown(self, user_id: str) -> None:
        """Record that we replied to this user right now."""
        self._cooldown_map[user_id] = time.time()

    def reset_cooldown(self, user_id: str) -> None:
        """Remove user from cooldown map (e.g. for negative sentiment priority)."""
        self._cooldown_map.pop(user_id, None)
```

- [ ] **Step 4: Update RAGPipeline**

Replace `backend/app/core/rag/pipeline.py` with:

```python
"""RAG Pipeline — orchestrates filter → embed → retrieve → override fetch → prompt → reply."""
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.core.ai.base import LLMResult
from app.core.rag.filter import CommentFilter

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """\
Bạn là AI assistant hỗ trợ bán hàng trên TikTok Live. Nhiệm vụ của bạn là trả lời \
câu hỏi từ người xem livestream dựa trên thông tin sản phẩm được cung cấp.

Quy tắc:
- Luôn trả lời bằng tiếng Việt
- Ngắn gọn, thân thiện (tối đa 2-3 câu)
- Chỉ dùng thông tin trong Context, không bịa đặt
- Nếu câu hỏi không liên quan đến sản phẩm/dịch vụ của shop, trả lời ngắn gọn: \
"Dạ bên em chuyên về [lĩnh vực shop], bên em không hỗ trợ vấn đề này ạ!" rồi kết thúc, không cần hỏi SĐT
- Nếu không có thông tin phù hợp trong Context, nói "Để em hỏi lại và phản hồi sau nhé ạ!"
- Tone: {tone}

{override_examples}\
Trả lời dưới dạng JSON với đúng 3 field:
- "intent": phân loại ý định của comment ("product_inquiry" | "greeting" | "complaint" | "spam" | "other")
- "sentiment": cảm xúc của comment ("positive" | "neutral" | "negative")
- "reply": nội dung trả lời"""


def _format_override_examples(overrides: list[tuple[str, str]]) -> str:
    """Format override examples for system prompt injection."""
    if not overrides:
        return ""
    lines = [
        "Dưới đây là một số ví dụ cách shop đã trả lời trước đó.",
        "Hãy học theo phong cách này:\n",
    ]
    for comment, reply in overrides:
        lines.append(f'Viewer: "{comment}"')
        lines.append(f'Shop: "{reply}"\n')
    return "\n".join(lines) + "\n"


@dataclass
class RAGResult:
    intent: str
    sentiment: str
    reply: str | None
    chunks_used: list[str]
    skipped: bool
    skip_reason: str | None = None


@dataclass
class RAGPipeline:
    """
    Orchestrates the full RAG comment-reply flow.

    Inject dependencies via constructor to keep this testable without
    real API calls or a running ChromaDB instance.
    """

    seller_id: str
    seller_settings: dict[str, Any]
    embed_fn: Callable[[str], Awaitable[list[float]]]
    retrieve_fn: Callable[[str, list[float], int], Awaitable[list[dict]]]
    generate_reply_fn: Callable[..., Awaitable[LLMResult]]
    fetch_overrides_fn: Callable[[str], Awaitable[list[tuple[str, str]]]]
    _filter: CommentFilter = field(init=False)

    def __post_init__(self) -> None:
        self._filter = CommentFilter(self.seller_settings)

    async def process(self, user_id: str, comment: str) -> RAGResult:
        """Process one comment through the full pipeline."""
        # 1. Filter
        filter_result = self._filter.check(user_id, comment)
        if filter_result.skip:
            logger.info("Comment skipped (reason=%s): %s", filter_result.reason, comment[:40])
            return RAGResult(
                intent="skipped",
                sentiment="neutral",
                reply=None,
                chunks_used=[],
                skipped=True,
                skip_reason=filter_result.reason,
            )

        # 2. Embed comment
        embedding = await self.embed_fn(comment)

        # 3. Retrieve top-3 chunks
        chunks = await self.retrieve_fn(self.seller_id, embedding, 3)

        # 4. Fetch recent seller override examples
        overrides = await self.fetch_overrides_fn(self.seller_id)

        # 5. Build context and system prompt
        context = "\n\n".join(c["content"] for c in chunks)
        override_block = _format_override_examples(overrides)
        system = SYSTEM_PROMPT_TEMPLATE.format(
            tone=self.seller_settings.get("tone", "friendly"),
            override_examples=override_block,
        )

        # 6. Generate structured reply (intent + sentiment + reply)
        llm_result: LLMResult = await self.generate_reply_fn(
            system=system,
            context=context,
            user_msg=comment,
        )

        # 7. Record cooldown
        self._filter.update_cooldown(user_id)

        logger.info(
            "Reply for %s (intent=%s, sentiment=%s): %s",
            user_id, llm_result.intent, llm_result.sentiment, llm_result.reply[:60],
        )
        return RAGResult(
            intent=llm_result.intent,
            sentiment=llm_result.sentiment,
            reply=llm_result.reply,
            chunks_used=[c["id"] for c in chunks],
            skipped=False,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_pipeline.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/rag/pipeline.py backend/app/core/rag/filter.py backend/tests/test_pipeline.py
git commit -m "feat: update RAGPipeline for structured LLM output with override examples and sentiment"
```

---

### Task 9: Add `get_recent_overrides` Query Function

**Files:**
- Create: `backend/app/core/rag/overrides.py`
- Test: `backend/tests/test_override_examples.py`

- [ ] **Step 1: Write tests for override fetching**

Create `backend/tests/test_override_examples.py`:

```python
"""Tests for fetching recent seller override examples."""
import pytest

from app.core.rag.overrides import get_recent_overrides
from app.models.message import MessageLog
from app.models.session import LiveSession, SessionStatus


@pytest.mark.asyncio
async def test_get_recent_overrides_returns_manual_replies(db_session, test_seller):
    """Fetches manual override (comment, reply) pairs for a seller."""
    session = LiveSession(seller_id=test_seller.id, status=SessionStatus.ENDED)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # Create a manual override message
    msg = MessageLog(
        session_id=session.id,
        user_unique_id="viewer1",
        comment="Giá bao nhiêu?",
        reply="Dạ 150k thôi ạ!",
        intent="manual",
    )
    db_session.add(msg)
    await db_session.commit()

    overrides = await get_recent_overrides(test_seller.id, db_session, limit=5)

    assert len(overrides) == 1
    assert overrides[0] == ("Giá bao nhiêu?", "Dạ 150k thôi ạ!")


@pytest.mark.asyncio
async def test_get_recent_overrides_excludes_bot_replies(db_session, test_seller):
    """Only returns messages with intent='manual', not bot-generated replies."""
    session = LiveSession(seller_id=test_seller.id, status=SessionStatus.ENDED)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # Bot reply (intent != "manual")
    bot_msg = MessageLog(
        session_id=session.id,
        user_unique_id="viewer1",
        comment="Hello",
        reply="Chào bạn!",
        intent="greeting",
    )
    # Manual override
    manual_msg = MessageLog(
        session_id=session.id,
        user_unique_id="viewer2",
        comment="Ship lâu không?",
        reply="Dạ 2-3 ngày ạ!",
        intent="manual",
    )
    db_session.add_all([bot_msg, manual_msg])
    await db_session.commit()

    overrides = await get_recent_overrides(test_seller.id, db_session, limit=5)

    assert len(overrides) == 1
    assert overrides[0][0] == "Ship lâu không?"


@pytest.mark.asyncio
async def test_get_recent_overrides_respects_limit(db_session, test_seller):
    """Returns at most `limit` overrides, most recent first."""
    session = LiveSession(seller_id=test_seller.id, status=SessionStatus.ENDED)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    for i in range(10):
        msg = MessageLog(
            session_id=session.id,
            user_unique_id=f"viewer{i}",
            comment=f"Question {i}",
            reply=f"Answer {i}",
            intent="manual",
        )
        db_session.add(msg)
    await db_session.commit()

    overrides = await get_recent_overrides(test_seller.id, db_session, limit=5)

    assert len(overrides) == 5


@pytest.mark.asyncio
async def test_get_recent_overrides_empty_for_new_seller(db_session, test_seller):
    """Returns empty list when seller has no manual overrides."""
    overrides = await get_recent_overrides(test_seller.id, db_session, limit=5)
    assert overrides == []


@pytest.mark.asyncio
async def test_get_recent_overrides_excludes_other_sellers(db_session, test_seller):
    """Only returns overrides from the specified seller, not other sellers."""
    # Create a session for test_seller
    session = LiveSession(seller_id=test_seller.id, status=SessionStatus.ENDED)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    msg = MessageLog(
        session_id=session.id,
        user_unique_id="viewer1",
        comment="My question",
        reply="My answer",
        intent="manual",
    )
    db_session.add(msg)

    # Create a session for a different seller
    other_session = LiveSession(seller_id="other-seller-id", status=SessionStatus.ENDED)
    db_session.add(other_session)
    await db_session.commit()
    await db_session.refresh(other_session)

    other_msg = MessageLog(
        session_id=other_session.id,
        user_unique_id="viewer2",
        comment="Other question",
        reply="Other answer",
        intent="manual",
    )
    db_session.add(other_msg)
    await db_session.commit()

    overrides = await get_recent_overrides(test_seller.id, db_session, limit=5)

    assert len(overrides) == 1
    assert overrides[0][0] == "My question"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_override_examples.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.rag.overrides'`

- [ ] **Step 3: Implement get_recent_overrides**

Create `backend/app/core/rag/overrides.py`:

```python
"""Fetch recent seller manual override examples for few-shot prompt injection."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import MessageLog
from app.models.session import LiveSession

logger = logging.getLogger(__name__)


async def get_recent_overrides(
    seller_id: str,
    db: AsyncSession,
    limit: int = 5,
) -> list[tuple[str, str]]:
    """Return (comment, reply) pairs from recent manual overrides for a seller.

    Queries MessageLog entries where intent='manual' and reply is not null,
    joined through LiveSession to filter by seller_id.
    Results are ordered by created_at DESC and limited.
    """
    result = await db.execute(
        select(MessageLog.comment, MessageLog.reply)
        .join(LiveSession, MessageLog.session_id == LiveSession.id)
        .where(
            LiveSession.seller_id == seller_id,
            MessageLog.intent == "manual",
            MessageLog.reply.is_not(None),
        )
        .order_by(MessageLog.created_at.desc())
        .limit(limit)
    )
    rows = result.all()
    return [(row[0], row[1]) for row in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_override_examples.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/rag/overrides.py backend/tests/test_override_examples.py
git commit -m "feat: add get_recent_overrides query for few-shot prompt injection"
```

---

### Task 10: Update `_handle_comment` in Sessions API

**Files:**
- Modify: `backend/app/api/v1/sessions.py`

- [ ] **Step 1: Update `_build_pipeline` to accept a `fetch_overrides_fn`**

In `backend/app/api/v1/sessions.py`, update the imports at the top:

Add these imports:
```python
from app.core.rag.overrides import get_recent_overrides
```

Remove this import (no longer needed):
```python
from app.core.rag.filter import detect_intent   # DELETE if present in imports
```

Update `_build_pipeline` (currently lines 41-50) to:

```python
def _build_pipeline(seller: Seller, fetch_overrides_fn) -> RAGPipeline:
    embed_provider = get_embed_provider()
    reply_provider = get_reply_provider()
    return RAGPipeline(
        seller_id=seller.id,
        seller_settings=seller.bot_settings,
        embed_fn=embed_provider.embed,
        retrieve_fn=retriever.query,
        generate_reply_fn=reply_provider.generate_reply,
        fetch_overrides_fn=fetch_overrides_fn,
    )
```

- [ ] **Step 2: Update `_handle_comment` for sentiment handling**

Update `_handle_comment` (currently lines 53-133). The key changes are:
1. Save `sentiment` from RAG result to DB
2. Broadcast `sentiment` in reply message
3. Broadcast alert for negative sentiment
4. Reset cooldown for negative sentiment

Replace the `_handle_comment` function with:

```python
async def _handle_comment(seller_id: str, user: str, text: str) -> None:
    """Background callback: filter → RAG → save → reply → broadcast."""
    state = get_session_state(seller_id)

    if state.bot_paused or state.active_pipeline is None or state.active_session_id is None:
        return

    max_replies = state.active_pipeline.seller_settings.get("max_replies_per_session", 500)
    if state.reply_count >= max_replies:
        logger.info("Max replies reached (%d), skipping", max_replies)
        return

    # Save incoming comment (intent/sentiment updated after LLM)
    async with get_session_factory()() as db:
        msg = MessageLog(
            session_id=state.active_session_id,
            user_unique_id=user,
            comment=text,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        message_id = msg.id

    # Broadcast comment to dashboard
    await broadcast(
        {
            "type": "comment",
            "seller_id": seller_id,
            "message_id": message_id,
            "user": user,
            "content": text,
            "timestamp": msg.created_at.isoformat() if msg.created_at else None,
        }
    )

    # Run RAG pipeline (now returns intent + sentiment + reply)
    result = await state.active_pipeline.process(user, text)

    # Update message with intent and sentiment regardless of skip
    async with get_session_factory()() as db:
        msg = await db.get(MessageLog, message_id)
        if msg:
            msg.intent = result.intent
            msg.sentiment = result.sentiment
            await db.commit()

    if result.skipped:
        return

    # Send reply via TikTok
    if state.active_replier:
        try:
            await state.active_replier.send(result.reply)
            state.reply_count += 1
        except Exception:
            logger.exception("Failed to send reply for %s", user)
            return

    # Persist reply and chunks to DB
    async with get_session_factory()() as db:
        msg = await db.get(MessageLog, message_id)
        if msg:
            msg.reply = result.reply
            msg.chunks_used = result.chunks_used
            await db.commit()

    # Broadcast reply to dashboard (with sentiment)
    await broadcast(
        {
            "type": "reply",
            "seller_id": seller_id,
            "message_id": message_id,
            "content": result.reply,
            "intent": result.intent,
            "sentiment": result.sentiment,
            "chunks_used": result.chunks_used,
        }
    )

    # Negative sentiment: alert dashboard + bypass cooldown for this user
    if result.sentiment == "negative":
        await broadcast(
            {
                "type": "alert",
                "seller_id": seller_id,
                "severity": "negative",
                "message_id": message_id,
                "comment": text,
                "user": user,
            }
        )
        state.active_pipeline._filter.reset_cooldown(user)
```

- [ ] **Step 3: Update `start_session` to pass `fetch_overrides_fn`**

In the `start_session` function, update the line that builds the pipeline (currently line 186):

```python
        # Build fetch_overrides_fn bound to seller_id
        async def _fetch_overrides(sid: str) -> list[tuple[str, str]]:
            async with get_session_factory()() as db:
                return await get_recent_overrides(sid, db, limit=5)

        pipeline = _build_pipeline(current_seller, _fetch_overrides)
```

- [ ] **Step 4: Run existing session wiring tests to verify nothing breaks**

Run: `python3 -m pytest tests/test_session_wiring.py -v`
Expected: Some tests may FAIL due to mocked `generate_reply` returning `str` instead of `LLMResult` — this will be fixed in Task 11.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/sessions.py
git commit -m "feat: update sessions API for structured LLM output, sentiment alerts, and override injection"
```

---

### Task 11: Update Test Fixtures and Session Wiring Tests

**Files:**
- Modify: `backend/tests/test_session_wiring.py`

- [ ] **Step 1: Update test mocks to return LLMResult**

Replace `backend/tests/test_session_wiring.py` with:

```python
"""Integration tests for session start/stop/status with multi-tenant auth."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.ai.base import LLMResult


async def test_start_session_creates_live_session(auth_client, test_seller):
    """POST /api/v1/sessions/start creates LiveSession with ACTIVE status."""
    with (
        patch("app.api.v1.sessions.TikTokLiveClient") as mock_tiktok_cls,
        patch("app.api.v1.sessions.LiveListener") as mock_listener_cls,
        patch("app.api.v1.sessions.get_embed_provider") as mock_embed_factory,
        patch("app.api.v1.sessions.get_reply_provider") as mock_reply_factory,
    ):
        mock_tiktok = MagicMock()
        mock_tiktok.web = MagicMock()
        mock_tiktok_cls.return_value = mock_tiktok

        mock_listener = MagicMock()
        mock_listener.start = AsyncMock()
        mock_listener_cls.return_value = mock_listener

        mock_embed_factory.return_value = AsyncMock()
        mock_reply_provider = AsyncMock()
        mock_reply_provider.generate_reply = AsyncMock(
            return_value=LLMResult(intent="greeting", sentiment="neutral", reply="Chào!")
        )
        mock_reply_factory.return_value = mock_reply_provider

        # No body needed - seller_id comes from JWT
        resp = await auth_client.post("/api/v1/sessions/start")

    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["session"]["status"] == "active"
    assert data["session"]["seller_id"] == test_seller.id


async def test_start_session_twice_returns_400(auth_client, test_seller):
    """Cannot start a second session while one is already active."""
    with (
        patch("app.api.v1.sessions.TikTokLiveClient") as mock_tiktok_cls,
        patch("app.api.v1.sessions.LiveListener") as mock_listener_cls,
        patch("app.api.v1.sessions.get_embed_provider") as mock_embed_factory,
        patch("app.api.v1.sessions.get_reply_provider") as mock_reply_factory,
    ):
        mock_tiktok = MagicMock()
        mock_tiktok.web = MagicMock()
        mock_tiktok_cls.return_value = mock_tiktok

        mock_listener = MagicMock()
        mock_listener_cls.return_value = mock_listener

        mock_embed_factory.return_value = AsyncMock()
        mock_reply_factory.return_value = AsyncMock()

        await auth_client.post("/api/v1/sessions/start")
        resp2 = await auth_client.post("/api/v1/sessions/start")

    assert resp2.status_code == 400


async def test_stop_session(auth_client, test_seller):
    """POST /api/v1/sessions/stop ends active session."""
    with (
        patch("app.api.v1.sessions.TikTokLiveClient") as mock_tiktok_cls,
        patch("app.api.v1.sessions.LiveListener") as mock_listener_cls,
        patch("app.api.v1.sessions.get_embed_provider") as mock_embed_factory,
        patch("app.api.v1.sessions.get_reply_provider") as mock_reply_factory,
    ):
        mock_tiktok = MagicMock()
        mock_tiktok.web = MagicMock()
        mock_tiktok_cls.return_value = mock_tiktok

        mock_listener = MagicMock()
        mock_listener.stop = AsyncMock()
        mock_listener_cls.return_value = mock_listener

        mock_embed_factory.return_value = AsyncMock()
        mock_reply_factory.return_value = AsyncMock()

        await auth_client.post("/api/v1/sessions/start")

    resp = await auth_client.post("/api/v1/sessions/stop")
    assert resp.status_code == 200


async def test_stop_when_no_active_session_returns_400(auth_client, test_seller):
    """POST /stop with no active session returns 400."""
    resp = await auth_client.post("/api/v1/sessions/stop")
    assert resp.status_code == 400


async def test_history_returns_list(auth_client, test_seller):
    """GET /api/v1/sessions/history returns list of past sessions (only for authenticated seller)."""
    resp = await auth_client.get("/api/v1/sessions/history?page=1&limit=20")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_session_wiring.py -v`
Expected: PASS (5 tests)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_session_wiring.py
git commit -m "test: update session wiring tests for LLMResult structured output"
```

---

### Task 12: Update Settings API (`test-reply`) and Schemas

**Files:**
- Modify: `backend/app/api/v1/settings.py`
- Modify: `backend/app/schemas/settings.py`
- Modify: `backend/app/schemas/session.py`
- Modify: `backend/tests/test_settings_api.py`

- [ ] **Step 1: Update schemas**

In `backend/app/schemas/settings.py`, update `TestReplyResponse` (line 33-36) to include `sentiment`:

```python
class TestReplyResponse(BaseModel):
    reply: str
    intent: str
    sentiment: str
    chunks_used: list[str]
```

In `backend/app/schemas/session.py`, add `sentiment` to `MessageLogResponse` (after line 33):

```python
class MessageLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    session_id: str
    user_unique_id: str
    comment: str
    reply: str | None
    intent: str
    sentiment: str = "neutral"
    chunks_used: list[str]
    created_at: datetime
```

- [ ] **Step 2: Update `test_reply` endpoint in settings.py**

In `backend/app/api/v1/settings.py`, update the imports: remove `detect_intent` import, add `LLMResult` and `get_recent_overrides` imports:

```python
from app.core.ai.base import LLMResult
from app.core.rag.overrides import get_recent_overrides
from app.core.rag.pipeline import SYSTEM_PROMPT_TEMPLATE, _format_override_examples
```

Remove this import line:
```python
from app.core.rag.filter import detect_intent   # DELETE
```

Replace the `test_reply` function (lines 53-90) with:

```python
@router.post("/test-reply", response_model=TestReplyResponse)
async def test_reply(
    body: TestReplyRequest,
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
):
    """Run the full RAG pipeline for a comment and return the preview reply.
    Does NOT send anything to TikTok."""
    settings = current_seller.bot_settings
    seller_id = current_seller.id

    # Blacklist check
    blacklist = settings.get("blacklist_keywords", [])
    comment_lower = body.comment.lower()
    if any(kw.lower() in comment_lower for kw in blacklist):
        return TestReplyResponse(
            reply="[Bị chặn] Comment chứa từ khoá bị cấm.",
            intent="blacklist",
            sentiment="neutral",
            chunks_used=[],
        )

    embed_provider = get_embed_provider()
    embedding = await embed_provider.embed(body.comment)

    chunks = await retriever.query(seller_id, embedding, n_results=3)
    context = "\n\n".join(c["content"] for c in chunks)

    # Fetch override examples and build prompt
    overrides = await get_recent_overrides(seller_id, db, limit=5)
    override_block = _format_override_examples(overrides)
    system = SYSTEM_PROMPT_TEMPLATE.format(
        tone=settings.get("tone", "friendly"),
        override_examples=override_block,
    )

    reply_provider = get_reply_provider()
    llm_result: LLMResult = await reply_provider.generate_reply(
        system=system, context=context, user_msg=body.comment
    )

    return TestReplyResponse(
        reply=llm_result.reply,
        intent=llm_result.intent,
        sentiment=llm_result.sentiment,
        chunks_used=[c["id"] for c in chunks],
    )
```

- [ ] **Step 3: Update test for test-reply**

In `backend/tests/test_settings_api.py`, update the `test_test_reply` function. The mock for `generate_reply` must return `LLMResult` instead of `str`:

```python
async def test_test_reply(auth_client, test_seller):
    """POST /api/v1/settings/test-reply returns a preview reply without sending to TikTok."""
    from app.core.ai.base import LLMResult

    with (
        patch("app.api.v1.settings.get_embed_provider") as mock_embed_factory,
        patch("app.api.v1.settings.retriever.query", new_callable=AsyncMock) as mock_query,
        patch("app.api.v1.settings.get_reply_provider") as mock_reply_factory,
        patch("app.api.v1.settings.get_recent_overrides", new_callable=AsyncMock) as mock_overrides,
    ):
        mock_embed_provider = AsyncMock()
        mock_embed_provider.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_factory.return_value = mock_embed_provider

        mock_query.return_value = [
            {"id": "c1", "content": "Áo giá 150k", "metadata": {}, "distance": 0.1}
        ]

        mock_reply_provider = AsyncMock()
        mock_reply_provider.generate_reply = AsyncMock(
            return_value=LLMResult(
                intent="product_inquiry",
                sentiment="neutral",
                reply="Dạ giá 150k ạ!",
            )
        )
        mock_reply_factory.return_value = mock_reply_provider

        mock_overrides.return_value = []

        resp = await auth_client.post(
            "/api/v1/settings/test-reply",
            json={
                "comment": "Giá bao nhiêu?",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"] == "Dạ giá 150k ạ!"
    assert data["intent"] == "product_inquiry"
    assert data["sentiment"] == "neutral"
    assert "chunks_used" in data
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_settings_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/settings.py backend/app/schemas/settings.py backend/app/schemas/session.py backend/tests/test_settings_api.py
git commit -m "feat: update settings test-reply for structured output with sentiment, update schemas"
```

---

### Task 13: Update Analytics API for Sentiment Breakdown

**Files:**
- Modify: `backend/app/schemas/analytics.py`
- Modify: `backend/app/api/v1/analytics.py`
- Modify: `backend/tests/test_analytics_api.py`

- [ ] **Step 1: Update AnalyticsResponse schema**

In `backend/app/schemas/analytics.py`, add `sentiment_breakdown`:

```python
from pydantic import BaseModel, Field


class AnalyticsResponse(BaseModel):
    total_sessions: int
    total_comments: int
    total_replies: int
    reply_rate: float  # 0-100
    intent_breakdown: dict[str, int] = Field(default_factory=dict, description="Intent label to count mapping")
    sentiment_breakdown: dict[str, int] = Field(default_factory=dict, description="Sentiment label to count mapping")
    unanswered_count: int
```

- [ ] **Step 2: Update analytics endpoint**

In `backend/app/api/v1/analytics.py`, add the sentiment breakdown query. After the existing `intent_breakdown` computation, add:

```python
    # Sentiment breakdown
    sentiment_q = await db.execute(
        select(MessageLog.sentiment, func.count(MessageLog.id))
        .join(LiveSession, MessageLog.session_id == LiveSession.id)
        .where(LiveSession.seller_id == seller_id, *date_filters)
        .group_by(MessageLog.sentiment)
    )
    sentiment_breakdown = dict(sentiment_q.all())
```

And add `sentiment_breakdown=sentiment_breakdown` to the `AnalyticsResponse(...)` return.

The existing `date_filters` variable (used for intent_breakdown) should be reused. If `date_filters` is defined inline, extract it to a shared variable first.

Full updated return statement:

```python
    return AnalyticsResponse(
        total_sessions=total_sessions,
        total_comments=total_comments,
        total_replies=total_replies,
        reply_rate=round(reply_rate, 1),
        intent_breakdown=intent_breakdown,
        sentiment_breakdown=sentiment_breakdown,
        unanswered_count=unanswered_count,
    )
```

- [ ] **Step 3: Update analytics test**

In `backend/tests/test_analytics_api.py`, update the first test to check for `sentiment_breakdown`:

```python
async def test_analytics_returns_zeros_for_new_seller(auth_client: AsyncClient, test_seller):
    """GET /api/v1/analytics/ returns zero stats for authenticated seller with no data."""
    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 0
    assert data["total_comments"] == 0
    assert data["total_replies"] == 0
    assert data["reply_rate"] == 0.0
    assert data["intent_breakdown"] == {}
    assert data["sentiment_breakdown"] == {}
    assert data["unanswered_count"] == 0
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_analytics_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/analytics.py backend/app/api/v1/analytics.py backend/tests/test_analytics_api.py
git commit -m "feat: add sentiment_breakdown to analytics API response"
```

---

### Task 14: Run Full Test Suite and Fix Any Failures

**Files:**
- Any files that need fixing

- [ ] **Step 1: Run the full backend test suite**

Run: `python3 -m pytest tests/ --ignore=tests/test_ai_providers.py -v`
Expected: All tests pass (the 3 pre-existing `test_ai_providers.py` failures are excluded).

- [ ] **Step 2: Fix any failing tests**

If any tests fail due to:
- Import errors from removed `detect_intent` — update imports
- Missing `sentiment` field in mock data — add `sentiment="neutral"` to test fixtures
- `RAGPipeline` constructor missing `fetch_overrides_fn` — add `fetch_overrides_fn=AsyncMock(return_value=[])` to mocks

Fix each failure and re-run until all pass.

- [ ] **Step 3: Run Alembic migration check**

Run: `python3 -m alembic check`
Expected: No pending migrations (or run `python3 -m alembic upgrade head` if needed).

- [ ] **Step 4: Verify backend imports**

Run: `python3 -c "from app.main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve test failures from structured output migration"
```

---

### Task 15: Frontend Build Verification

**Files:**
- None (verification only)

- [ ] **Step 1: Run frontend build**

Run (from `frontend/` directory): `npm run build`
Expected: Build succeeds with no errors. Frontend is unchanged in this plan but verify nothing broke.

- [ ] **Step 2: Final commit if needed**

If any changes were needed:
```bash
git add -A
git commit -m "fix: resolve frontend build issues"
```
