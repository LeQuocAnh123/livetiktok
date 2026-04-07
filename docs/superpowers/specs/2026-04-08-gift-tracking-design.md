# Gift Tracking — Design Spec

**Date:** 2026-04-08
**Status:** Approved
**Scope:** Real-time gift tracking, LLM-generated thank-you replies, revenue analytics

## Overview

Integrate TikTokLive `GiftEvent` into the existing pipeline to track gifts in real-time, automatically thank gifters via LLM, and surface gift/revenue analytics on the dashboard.

## Architecture: Extend Existing Pipeline (Approach A)

Gift events flow through a lightweight variant of the RAG pipeline — reusing `generate_reply_fn` and seller settings but skipping embedding and retrieval (gifts don't need knowledge base context).

## Data Model

### New table: `gift_logs`

| Column | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `session_id` | FK -> live_sessions.id | NOT NULL |
| `user_unique_id` | String | Viewer who sent gift |
| `gift_name` | String | "Rose", "Lion", etc. |
| `diamond_count` | Integer | Diamonds per unit |
| `repeat_count` | Integer | Total count (after streak ends) |
| `total_diamonds` | Integer | `diamond_count * repeat_count` (denormalized) |
| `estimated_usd` | Float | `total_diamonds * 0.005` |
| `thank_reply` | String (nullable) | LLM-generated thank-you message |
| `created_at` | DateTime | Server default |

**Relationships:** `LiveSession.gifts` (1:N GiftLog)

**Idempotency:** Index on `(session_id, user_unique_id, gift_name, created_at)` to detect duplicate events from TikTok reconnects.

**Alembic migration** adds the table + index.

## Event Flow

```
TikTok Live Stream
    │
    ├── CommentEvent ──> LiveListener._on_comment() ──> _handle_comment() [existing]
    │
    └── GiftEvent ──> LiveListener._on_gift() [NEW]
            │
            ├── if gift.streakable and not repeat_end: SKIP (wait for streak end)
            │
            └── else: _handle_gift(user, gift_name, diamond_count, repeat_count)
                    │
                    ├── 1. Save GiftLog to DB (before reply)
                    │
                    ├── 2. Broadcast WebSocket "gift" message to dashboard
                    │
                    ├── 3. Build gift context string:
                    │   "Viewer {user} vừa tặng {repeat_count}x {gift_name}
                    │    ({total_diamonds} diamonds, ~${usd})"
                    │
                    ├── 4. Call RAGPipeline.process_gift(user, gift_context)
                    │   - Skip embed/retrieve (no chunks)
                    │   - System prompt: seller tone + gift thank instruction
                    │   - generate_reply_fn(system, "", gift_context) -> LLMResult
                    │   - Fixed intent="gift_thank", sentiment from LLM
                    │
                    ├── 5. Send reply to TikTok chat via Replier
                    │
                    ├── 6. Update GiftLog.thank_reply
                    │
                    └── 7. Broadcast WebSocket "gift_reply" message
```

### Streak Handling

TikTok gifts can be "streakable" — viewer holds the send button to gift multiple times in rapid succession. The `GiftEvent` fires for each increment with `streaking=True` and `repeat_end=False`, then a final event with `repeat_end=True`.

**Decision:** Only process the final event (`repeat_end=True` or `streakable=False`). This avoids spamming chat and gives an accurate total count.

### Settings Interaction

- Gift thank-you respects `bot_paused` and `auto_reply_enabled` — if either disables the bot, gifts are still **logged** but no reply is sent.
- Per-user cooldown does **NOT** apply to gift thanks — gifts are special events that always deserve acknowledgment.
- Seller `tone` setting applies to gift thank-you prompts (same personality as comment replies).

## RAGPipeline Extension

### New method: `process_gift(user_id: str, gift_context: str) -> GiftReplyResult`

```python
@dataclass
class GiftReplyResult:
    reply: str
    sentiment: str  # from LLM analysis of gift context
```

Implementation:
1. Build system prompt with seller tone + Vietnamese instruction: "Hãy cảm ơn viewer đã tặng gift. Trả lời ngắn gọn, chân thành, phù hợp với tone."
2. Call `generate_reply_fn(system_prompt, "", gift_context)` — empty context string (no RAG chunks)
3. Extract `reply` and `sentiment` from `LLMResult`
4. No cooldown update, no intent classification (fixed as `gift_thank`)

## WebSocket Messages

### New server -> client message types

| Type | Fields | When |
|---|---|---|
| `gift` | `seller_id, gift_log_id, user, gift_name, diamond_count, repeat_count, total_diamonds, estimated_usd, timestamp` | Gift received (after streak end) |
| `gift_reply` | `seller_id, gift_log_id, content, user` | LLM thank-you sent |

## API Endpoints

### Modified: `GET /api/v1/analytics/`

Add `gift_stats` to `AnalyticsResponse`:

```python
class GiftStats(BaseModel):
    total_gifts: int            # count of gift_logs
    total_diamonds: int         # sum of total_diamonds
    estimated_usd: float        # sum of estimated_usd
    top_gifters: list[TopGifter]    # top 5 by total_diamonds
    gift_breakdown: list[GiftBreakdown]  # by gift type

class TopGifter(BaseModel):
    user: str
    total_diamonds: int
    gift_count: int

class GiftBreakdown(BaseModel):
    gift_name: str
    count: int
    total_diamonds: int
```

### New: `GET /api/v1/sessions/{session_id}/gifts`

Returns paginated list of `GiftLog` entries for a session. Response schema:

```python
class GiftLogResponse(BaseModel):
    id: str
    user_unique_id: str
    gift_name: str
    diamond_count: int
    repeat_count: int
    total_diamonds: int
    estimated_usd: float
    thank_reply: str | None
    created_at: datetime
```

## Frontend Changes

### Monitor Page

- **GiftFeed component** (new) — real-time scrolling list of gifts, displayed alongside CommentFeed
  - Each entry shows: gift icon, gift name, viewer username, diamond count, USD estimate
  - LLM thank-you reply displayed inline below gift entry (when available)
  - Styled differently from comments (highlight color, gift icon from Lucide)
- **Layout:** 2-column on desktop (CommentFeed left, GiftFeed right). Stack vertically on mobile.

### Analytics Page

- **2 new stat cards:** Total Diamonds, Estimated Revenue (USD)
- **Top Gifters mini-table:** Top 5 gifters with diamonds + gift count
- **Gift Type Breakdown:** Horizontal bar chart (same style as IntentBreakdown)

### TypeScript Types

Update `frontend/lib/api.ts`:
- Add `GiftStats`, `TopGifter`, `GiftBreakdown` types
- Add `gift_stats` to `AnalyticsData`
- Add `api.sessions.gifts(sessionId)` method
- Add `gift` and `gift_reply` WebSocket message handlers

## Error Handling

| Scenario | Behavior |
|---|---|
| LLM failure on gift thank | Log error, gift saved to DB, no reply sent (graceful degradation) |
| Free gifts (0 diamonds) | Still tracked and thanked — diamonds show as 0 |
| Duplicate GiftEvent (reconnect) | Skip via unique index on `(session_id, user_unique_id, gift_name, created_at)` |
| TikTok chat send failure | Log error, `thank_reply` still saved to DB for analytics |

## Testing Strategy

### Unit Tests
- `GiftLog` model creation + relationships
- `process_gift()` pipeline method with mocked LLM
- Streak filtering logic (streakable + repeat_end combinations)
- Gift analytics query aggregation

### Integration Tests
- `_handle_gift` end-to-end with mocked TikTok client + real DB
- WebSocket broadcast of gift + gift_reply messages

### API Tests
- Analytics endpoint returns `gift_stats` correctly
- Session gifts endpoint with pagination
- Empty state (no gifts) returns zeroes

## Out of Scope

- Gift leaderboard page (separate feature, can add later)
- Custom gift thank-you templates per tier (using LLM instead)
- Gift-triggered actions (e.g., play sound, show animation) — frontend only shows data
- Multi-platform gift support (deferred to multi-platform sub-project)
