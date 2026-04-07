# LLM-Based Classification, Sentiment Analysis & Learning from Overrides

**Date:** 2026-04-08  
**Status:** Approved  

## Overview

Three features unified into a single-LLM-call architecture:

1. **LLM-based intent classification** — replace keyword matching `detect_intent()` with LLM classification as part of reply generation
2. **Learning from manual overrides** — inject recent seller override examples as few-shot examples into the system prompt
3. **Sentiment analysis** — detect negative/complaint comments to ensure they always get replied to and alert sellers in real-time

## Core Principle: Single LLM Call

All three features are handled in **one LLM call** that returns structured JSON output:

```json
{
  "intent": "product_inquiry",
  "sentiment": "negative",
  "reply": "Dạ em xin lỗi anh/chị, để em check lại đơn ngay ạ!"
}
```

This avoids 2-3x latency and cost of separate classification calls.

## Architecture

### Pipeline Flow

**Current:**
```
filter → detect_intent (keyword) → embed → retrieve → build_prompt → generate_reply(→str) → update cooldown
```

**New:**
```
filter → embed → retrieve → fetch_overrides → build_prompt → generate_reply(→LLMResult) → sentiment_check → update cooldown
```

Key changes:
- `detect_intent()` removed from pipeline — LLM classifies intent as part of reply generation
- `fetch_overrides()` added — queries 5 most recent manual overrides for few-shot injection
- `generate_reply()` returns `LLMResult` (structured) instead of `str`
- After LLM response, negative sentiment triggers cooldown bypass + dashboard alert

### AIProvider Interface Change

**File:** `backend/app/core/ai/base.py`

```python
@dataclass
class LLMResult:
    intent: str       # "product_inquiry" | "greeting" | "complaint" | "spam" | "other"
    sentiment: str    # "positive" | "neutral" | "negative"
    reply: str

class AIProvider(Protocol):
    async def generate_reply(self, system: str, context: str, user_msg: str) -> LLMResult
```

**Intent categories** (expanded from 3 → 5):

| Intent | Description |
|---|---|
| `product_inquiry` | Hỏi về sản phẩm, giá, ship, size, màu, thanh toán |
| `greeting` | Chào hỏi, hello, hi |
| `complaint` | Phàn nàn, khiếu nại, không hài lòng |
| `spam` | Quảng cáo, spam, không liên quan |
| `other` | Không rõ ý định |

**Sentiment values:**

| Sentiment | Description |
|---|---|
| `positive` | Khen, hào hứng, cảm ơn |
| `neutral` | Hỏi thông tin bình thường |
| `negative` | Phàn nàn, thất vọng, tức giận |

### Structured Output Per Provider

Each provider uses its native structured output mechanism:

| Provider | Mechanism | Fallback |
|---|---|---|
| Claude | `tool_use` with JSON schema | Parse raw text as JSON |
| OpenAI | `response_format: { type: "json_schema" }` | Parse raw text as JSON |
| Groq | `response_format: { type: "json_object" }` + JSON instruction in prompt | Parse raw text as JSON |
| Gemini | `response_mime_type: "application/json"` + schema | Parse raw text as JSON |

**Universal fallback:** If JSON parsing fails for any provider, return `LLMResult(intent="other", sentiment="neutral", reply=raw_text)`. This ensures the bot never crashes due to malformed LLM output.

### System Prompt Changes

**File:** `backend/app/core/rag/pipeline.py`

The template is extended to include classification instructions and few-shot override examples:

```
Bạn là AI assistant hỗ trợ bán hàng trên TikTok Live. Nhiệm vụ của bạn là trả lời
câu hỏi từ người xem livestream dựa trên thông tin sản phẩm được cung cấp.

Quy tắc:
- Luôn trả lời bằng tiếng Việt
- Ngắn gọn, thân thiện (tối đa 2-3 câu)
- Chỉ dùng thông tin trong Context, không bịa đặt
- Nếu câu hỏi không liên quan đến sản phẩm/dịch vụ của shop, trả lời ngắn gọn:
  "Dạ bên em chuyên về [lĩnh vực shop], bên em không hỗ trợ vấn đề này ạ!" rồi kết thúc
- Nếu không có thông tin phù hợp trong Context, nói
  "Để em hỏi lại và phản hồi sau nhé ạ!"
- Tone: {tone}

{override_examples}

Trả lời dưới dạng JSON với đúng 3 field:
- "intent": phân loại ý định của comment ("product_inquiry" | "greeting" | "complaint" | "spam" | "other")
- "sentiment": cảm xúc của comment ("positive" | "neutral" | "negative")  
- "reply": nội dung trả lời
```

### Few-Shot Override Examples (Learning)

**Mechanism:** When a seller manually overrides a reply (via WebSocket `manual_reply`), the existing `MessageLog` record is updated with `intent="manual"`. No new table needed.

**Fetching overrides:**

New async function `get_recent_overrides(seller_id: str, limit: int = 5)` queries:

```sql
SELECT comment, reply FROM message_logs
JOIN live_sessions ON message_logs.session_id = live_sessions.id
WHERE live_sessions.seller_id = :seller_id
  AND message_logs.intent = 'manual'
  AND message_logs.reply IS NOT NULL
ORDER BY message_logs.created_at DESC
LIMIT 5
```

Returns `list[tuple[str, str]]` — pairs of (viewer comment, seller reply).

**Prompt injection format** (only when overrides exist):

```
Dưới đây là một số ví dụ cách shop đã trả lời trước đó.
Hãy học theo phong cách này:

Viewer: "Giá bao nhiêu vậy shop?"
Shop: "Dạ sản phẩm này giá 150k thôi ạ, inbox em gửi link nha!"

Viewer: "Giao hàng lâu quá"
Shop: "Dạ em xin lỗi ạ, để em check lại đơn cho anh/chị ngay nha!"
```

When no overrides exist, `{override_examples}` is empty string — prompt works as before.

**Token budget:** 5 overrides × ~40 tokens each = ~200 extra tokens. Acceptable.

**Pipeline integration:** `RAGPipeline` receives a new dependency:
```python
fetch_overrides_fn: Callable[[str], Awaitable[list[tuple[str, str]]]]
```

Called in `process()` between retrieve and build_prompt.

### Negative Sentiment Handling (Priority)

Instead of a true priority queue (unnecessary given the real-time stream processing model), negative comments get two special treatments:

1. **Cooldown bypass:** After LLM returns `sentiment="negative"`, call `filter.reset_cooldown(user_id)` so the next comment from this user is not blocked by per-user cooldown. Ensures frustrated users can keep getting responses.

2. **Dashboard alert:** Broadcast a separate WebSocket message:
```json
{
  "type": "alert",
  "seller_id": "...",
  "severity": "negative",
  "message_id": "...",
  "comment": "...",
  "user": "..."
}
```
This allows the dashboard to highlight negative comments for seller attention.

**`CommentFilter` change:** Add `reset_cooldown(user_id: str)` method that removes the user from the internal `_cooldown_map`.

### RAGResult Update

```python
@dataclass
class RAGResult:
    intent: str
    sentiment: str          # NEW
    reply: str
    chunks_used: list[str]
    skipped: bool
    skip_reason: str | None
```

## Database Changes

### MessageLog Model

**File:** `backend/app/models/message.py`

Add one column:
```python
sentiment = Column(String, nullable=False, default="neutral")
```

Existing rows get default `"neutral"`. No data migration needed beyond the column addition.

### Alembic Migration

Single migration file:
- Add `sentiment` column to `message_logs` table (String, NOT NULL, default "neutral")

### No New Tables

Manual overrides are already stored in `MessageLog` with `intent="manual"`. We query this existing data for few-shot examples. No `seller_override_examples` table needed.

## Schema Changes

### AnalyticsResponse

Add `sentiment_breakdown` field:
```python
sentiment_breakdown: dict[str, int]  # {"positive": 10, "neutral": 85, "negative": 5}
```

Computed from `MessageLog.sentiment` GROUP BY count, same pattern as existing `intent_breakdown`.

### MessageLogResponse (session.py)

Add `sentiment` field:
```python
sentiment: str = "neutral"
```

### TestReplyResponse (settings.py)

Add `intent` and `sentiment` fields:
```python
intent: str
sentiment: str
```

The `/api/v1/settings/test-reply` endpoint now returns classification results along with the reply.

## WebSocket Broadcast Changes

Updated message payloads:

**Reply broadcast** — add `sentiment`:
```json
{"type": "reply", "seller_id": "...", "message_id": "...", "content": "...", "intent": "...", "sentiment": "neutral", "chunks_used": [...]}
```

**New alert broadcast** — for negative sentiment:
```json
{"type": "alert", "seller_id": "...", "severity": "negative", "message_id": "...", "comment": "...", "user": "..."}
```

## Files Changed

### Modified

| File | Change |
|---|---|
| `backend/app/core/ai/base.py` | Add `LLMResult` dataclass, update `AIProvider` protocol |
| `backend/app/core/ai/claude.py` | Structured output via `tool_use`, return `LLMResult` |
| `backend/app/core/ai/openai_llm.py` | Structured output via `json_schema`, return `LLMResult` |
| `backend/app/core/ai/groq_llm.py` | Structured output via `json_object`, return `LLMResult` |
| `backend/app/core/ai/gemini_llm.py` | Structured output via `response_mime_type`, return `LLMResult` |
| `backend/app/core/rag/pipeline.py` | Remove `detect_intent` call, add `fetch_overrides_fn`, update `RAGResult`, update prompt building |
| `backend/app/core/rag/filter.py` | Add `reset_cooldown()` method to `CommentFilter`. Remove `detect_intent` function and `_INTENT_KEYWORDS` dict (dead code — LLM handles classification now) |
| `backend/app/api/v1/sessions.py` | Update `_handle_comment` for sentiment broadcast + alert + cooldown bypass. Pass `fetch_overrides_fn` when building pipeline |
| `backend/app/api/v1/settings.py` | Update `test-reply` endpoint to use `LLMResult` |
| `backend/app/api/v1/analytics.py` | Add `sentiment_breakdown` to response |
| `backend/app/models/message.py` | Add `sentiment` column |
| `backend/app/schemas/analytics.py` | Add `sentiment_breakdown` field |
| `backend/app/schemas/session.py` | Add `sentiment` to `MessageLogResponse` |
| `backend/app/schemas/settings.py` | Add `intent` + `sentiment` to `TestReplyResponse` |
| `backend/alembic/versions/xxx_add_sentiment.py` | Migration for sentiment column |

### New Files

None.

### Not Touched

- `backend/app/core/rag/retriever.py` — ChromaDB logic unchanged
- `backend/app/core/tiktok/` — Listener + Replier unchanged
- `backend/app/core/crypto.py` — unchanged
- `backend/app/api/v1/auth.py`, `knowledge.py` — unchanged
- `frontend/` — no frontend changes in this scope

### Tests

| File | Change |
|---|---|
| `backend/tests/test_session_wiring.py` | Mock `generate_reply` to return `LLMResult` |
| `backend/tests/test_settings_api.py` | `test-reply` returns intent + sentiment |
| `backend/tests/test_analytics_api.py` | `sentiment_breakdown` in response |
| `backend/tests/test_llm_structured_output.py` | **New** — test JSON parsing + fallback for each provider |
| `backend/tests/test_override_examples.py` | **New** — test fetching + prompt injection of overrides |
