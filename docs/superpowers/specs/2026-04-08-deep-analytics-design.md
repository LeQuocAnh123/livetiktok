# Deep Analytics — Design Spec

## Goal

Add in-depth analytics to the TikTok Live AI Bot: intra-session activity timelines (heatmap), trending keyword extraction, engagement/proxy-conversion metrics, and a per-session detail page. All computed on read from existing `MessageLog` and `GiftLog` data — no new models or migrations required.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Conversion rate | Proxy metric (`product_inquiry` intent / total comments) | TikTok Live exposes no click data |
| Heatmap scope | Intra-session (5-min buckets within one live session) | Shows engagement peaks during a single stream |
| Keyword extraction | Word frequency (regex tokenize + Vietnamese stopwords) | No NLP dependency, fast, sufficient for short TikTok comments |
| Page structure | Overview (enhanced) + Session detail page | Aggregate overview + drilldown per session |
| Charting library | Recharts | Tree-shakable, shadcn/ui compatible, React-native |
| Architecture | Compute on read | Simple, no new tables, SQLite handles well for typical data volumes (hundreds to low thousands of comments per session) |

## Architecture Overview

```
Browser                          Backend
──────                          ───────
/analytics        ──GET /api/v1/analytics/──>    Existing endpoint (enhanced)
                                                  + sentiment_trend (daily)
                                                  + top_keywords_overall
                                                  + session_list (summary per session)

/analytics/       ──GET /api/v1/analytics/──>    New endpoint
  sessions/[id]      sessions/{session_id}        - timeline (5-min buckets)
                                                  - top_keywords (session)
                                                  - intent/sentiment breakdown
                                                  - engagement_metrics
```

All queries scoped to authenticated seller via JWT. No new database tables — everything is computed from existing `MessageLog`, `GiftLog`, and `LiveSession` tables.

## Backend

### New Files

#### `backend/app/core/analytics/keywords.py`

Keyword extraction module.

```python
VIETNAMESE_STOPWORDS: frozenset[str]  # ~120 common Vietnamese stopwords

def extract_keywords(comments: list[str], top_n: int = 20) -> list[dict[str, int | str]]:
    """Extract top keywords from a list of comment strings.
    
    Process:
    1. Lowercase + normalize
    2. Tokenize: regex r'[a-zA-ZÀ-ỹ0-9]+' (split on whitespace/punctuation)
    3. Filter: remove stopwords, words < 2 chars
    4. Count frequency
    5. Return top_n as [{"word": "giá", "count": 45}, ...]
    """
```

The stopwords set covers common Vietnamese function words ("của", "và", "là", "có", "cho", "không", "này", "đã", "được", "với", "để", "từ", "trong", "theo", etc.) plus common TikTok filler words ("ạ", "nha", "nhé", "ơi", "vậy", "thì").

#### `backend/app/core/analytics/timeline.py`

Time-bucketing module.

```python
@dataclass
class TimelineBucket:
    bucket_start: datetime
    bucket_end: datetime
    comment_count: int
    reply_count: int
    gift_count: int
    gift_diamonds: int

def compute_timeline(
    session_start: datetime,
    session_end: datetime | None,
    messages: list,      # MessageLog rows (need created_at, reply)
    gifts: list,         # GiftLog rows (need created_at, total_diamonds)
    bucket_minutes: int = 5,
) -> list[TimelineBucket]:
    """Compute time-bucketed activity for a session.
    
    Process:
    1. Determine total session duration (start → end, or start → last event)
    2. Create empty buckets every `bucket_minutes` minutes
    3. Assign each message/gift to its bucket via floor((event.created_at - session_start) / bucket_seconds)
    4. Return sorted list of buckets
    """
```

Bucketing is done in Python (not SQL) because SQLite's date/time functions are limited and the data fits comfortably in memory.

#### `backend/app/core/analytics/__init__.py`

Empty init file for the analytics subpackage.

### Modified Files

#### `backend/app/api/v1/analytics.py`

**Enhance existing `GET /api/v1/analytics/`:**

Add to the existing response:
- `sentiment_trend`: Daily aggregation of sentiment counts, last 30 days by default. Query: `GROUP BY date(MessageLog.created_at), MessageLog.sentiment`.
- `top_keywords_overall`: Run `extract_keywords()` on all comments within the date range. Limit to top 20.
- `session_list`: Summary per session within the date range: `{id, started_at, ended_at, duration_minutes, comment_count, reply_count, reply_rate, gift_count, gift_diamonds, top_intent}`. Ordered by `started_at DESC`.

**New endpoint: `GET /api/v1/analytics/sessions/{session_id}`:**

Parameters:
- `session_id`: path parameter (string, UUID)

Auth: Requires authenticated seller. Returns 404 if session not found, 403 if session belongs to another seller.

Response:

```json
{
  "session_info": {
    "id": "uuid",
    "started_at": "ISO datetime",
    "ended_at": "ISO datetime or null",
    "duration_minutes": 45.5
  },
  "summary": {
    "total_comments": 350,
    "total_replies": 300,
    "reply_rate": 85.7,
    "total_gifts": 15,
    "total_diamonds": 2500,
    "estimated_usd": 12.5
  },
  "timeline": [
    {
      "bucket_start": "ISO datetime",
      "bucket_end": "ISO datetime",
      "comment_count": 15,
      "reply_count": 12,
      "gift_count": 2,
      "gift_diamonds": 50
    }
  ],
  "top_keywords": [
    { "word": "giá", "count": 45 }
  ],
  "intent_breakdown": { "product_inquiry": 120, "greeting": 45 },
  "sentiment_breakdown": { "positive": 80, "neutral": 100, "negative": 20 },
  "engagement_metrics": {
    "product_inquiry_rate": 35.5,
    "unique_commenters": 85,
    "comments_per_minute_avg": 3.2,
    "peak_minute": "ISO datetime",
    "peak_comments": 12
  }
}
```

Implementation flow:
1. Fetch `LiveSession` by ID → verify ownership
2. Fetch all `MessageLog` rows for session (single query, all fields needed)
3. Fetch all `GiftLog` rows for session (single query)
4. Compute `timeline` via `compute_timeline()`
5. Compute `top_keywords` via `extract_keywords()`
6. Compute breakdowns via Python `Counter` on in-memory data
7. Compute engagement metrics from the same data
8. Return assembled response

All computation happens in Python on already-fetched data — 2 SQL queries total for the detail endpoint.

#### `backend/app/schemas/analytics.py`

Add new Pydantic models:

```python
class SessionInfo(BaseModel):
    id: str
    started_at: datetime
    ended_at: datetime | None
    duration_minutes: float

class SessionSummary(BaseModel):
    total_comments: int
    total_replies: int
    reply_rate: float
    total_gifts: int
    total_diamonds: int
    estimated_usd: float

class TimelineBucket(BaseModel):
    bucket_start: datetime
    bucket_end: datetime
    comment_count: int
    reply_count: int
    gift_count: int
    gift_diamonds: int

class KeywordEntry(BaseModel):
    word: str
    count: int

class EngagementMetrics(BaseModel):
    product_inquiry_rate: float    # percentage
    unique_commenters: int
    comments_per_minute_avg: float
    peak_minute: datetime | None
    peak_comments: int

class SessionAnalyticsResponse(BaseModel):
    session_info: SessionInfo
    summary: SessionSummary
    timeline: list[TimelineBucket]
    top_keywords: list[KeywordEntry]
    intent_breakdown: dict[str, int]
    sentiment_breakdown: dict[str, int]
    engagement_metrics: EngagementMetrics

# For enhanced overview
class SentimentTrendEntry(BaseModel):
    date: str  # "YYYY-MM-DD"
    positive: int
    neutral: int
    negative: int

class SessionListEntry(BaseModel):
    id: str
    started_at: datetime
    ended_at: datetime | None
    duration_minutes: float
    comment_count: int
    reply_count: int
    reply_rate: float
    gift_count: int
    gift_diamonds: int
    top_intent: str

# Enhance existing AnalyticsResponse (add 3 new fields, keep all existing)
class AnalyticsResponse(BaseModel):
    total_sessions: int
    total_comments: int
    total_replies: int
    reply_rate: float
    intent_breakdown: dict[str, int]
    sentiment_breakdown: dict[str, int]
    unanswered_count: int
    gift_stats: GiftStats | None
    # NEW fields below
    sentiment_trend: list[SentimentTrendEntry]
    top_keywords_overall: list[KeywordEntry]
    session_list: list[SessionListEntry]
```

### Tests

#### `backend/tests/test_keywords.py`

Unit tests for `extract_keywords()`:
- Returns correct top-N keywords from a list of comments
- Filters Vietnamese stopwords
- Handles empty input
- Handles single-character words
- Case-insensitive

#### `backend/tests/test_timeline.py`

Unit tests for `compute_timeline()`:
- Correct bucketing with 5-min intervals
- Handles session with no messages
- Handles gifts across buckets
- Handles session without end time (uses last event)

#### `backend/tests/test_session_analytics_api.py`

Integration tests for `GET /api/v1/analytics/sessions/{session_id}`:
- Returns full analytics for a session with data
- Returns 404 for nonexistent session
- Returns 403 for another seller's session
- Returns empty timeline for session with no messages
- Correct engagement metrics computation

#### `backend/tests/test_analytics_api.py` (modify)

Add tests for enhanced overview fields:
- `sentiment_trend` returns daily aggregation
- `top_keywords_overall` returns keywords across sessions
- `session_list` returns per-session summaries

## Frontend

### New Dependencies

- `recharts` — charting library for React. Install via `npm install recharts`.

### New Files

#### `frontend/app/analytics/sessions/[id]/page.tsx`

Session detail page. Fetches `api.analytics.session(id)` on mount. Renders:
1. Header: session date, duration, back button
2. Summary KPI cards (6 cards: comments, replies, rate, gifts, diamonds, USD)
3. Activity Timeline chart
4. Two-column: Keywords | Intent+Sentiment breakdowns
5. Engagement Metrics cards

Uses `"use client"` directive. Loading state with skeleton. Error state with message.

#### `frontend/components/analytics/SessionList.tsx`

Table component for session list on overview page.

Props: `{ sessions: SessionListEntry[] }`

- Columns: Date/Time, Duration, Comments, Reply Rate, Gifts, Top Intent
- Click row → `router.push(/analytics/sessions/${id})`
- Sorted by started_at DESC (already from API)
- Uses shadcn/ui `Table` component

#### `frontend/components/analytics/ActivityTimeline.tsx`

Recharts `ComposedChart` with:
- `Area` for comment_count (blue)
- `Bar` for gift_diamonds (amber)
- X axis: bucket_start formatted as "HH:mm"
- Y axis (left): comment count
- Y axis (right): diamond count
- Tooltip showing all metrics for the bucket
- Responsive container

Props: `{ data: TimelineBucket[] }`

#### `frontend/components/analytics/KeywordCloud.tsx`

Recharts horizontal `BarChart`:
- Y axis: keyword text
- X axis: count
- Sorted descending
- Top 15 keywords displayed
- Blue bars

Props: `{ keywords: KeywordEntry[] }`

#### `frontend/components/analytics/SentimentBreakdown.tsx`

Recharts `PieChart`:
- 3 slices: positive (green), neutral (gray), negative (red)
- Legend + percentage labels
- Center label showing total

Props: `{ data: Record<string, number> }`

#### `frontend/components/analytics/EngagementMetrics.tsx`

Grid of KPI cards:
- Product inquiry rate (%) — proxy conversion
- Unique commenters
- Avg comments/minute
- Peak minute + peak count

Props: `{ metrics: EngagementMetrics }`

#### `frontend/components/analytics/SentimentTrend.tsx`

Recharts `AreaChart` for daily sentiment trend on overview page:
- 3 stacked areas: positive (green), neutral (gray), negative (red)
- X axis: date
- Tooltip showing counts per sentiment per day

Props: `{ data: SentimentTrendEntry[] }`

### Modified Files

#### `frontend/lib/api.ts`

Add types:
- `SessionInfo`, `SessionSummary`, `TimelineBucket`, `KeywordEntry`, `EngagementMetrics`, `SessionAnalyticsResponse`
- `SentimentTrendEntry`, `SessionListEntry`

Update `AnalyticsData`:
- Add `sentiment_trend`, `top_keywords_overall`, `session_list`

Add API method:
```typescript
api.analytics = {
  overview(params) { ... },  // existing, enhanced
  session(sessionId: string): Promise<SessionAnalyticsResponse> {
    return request(`/api/v1/analytics/sessions/${sessionId}`, { method: "GET" });
  },
}
```

#### `frontend/app/analytics/page.tsx`

Add below existing sections:
1. `SentimentTrend` chart (daily sentiment over time)
2. `KeywordCloud` for overall top keywords
3. `SessionList` table at the bottom

## Error Handling

- Session detail endpoint: 404 if session not found, 403 if wrong seller
- Empty data: all components handle zero-data gracefully (show "Chưa có dữ liệu" messages)
- Keyword extraction on empty comments: returns empty list
- Timeline with no events: returns empty list
- Frontend: loading skeletons, error toast on API failure

## Performance Considerations

- Session detail: 2 SQL queries (messages + gifts), all computation in Python. For a typical session (500 comments, 50 gifts), this takes <50ms.
- Enhanced overview: existing queries + 3 new queries (sentiment trend, keywords, session list). All use existing indexes on `session_id` and `seller_id`.
- No new database indexes needed. Existing `ForeignKey` indexes on `MessageLog.session_id` and `GiftLog.session_id` are sufficient.
- Vietnamese stopwords set is a `frozenset` (O(1) lookup). Keyword extraction on 1000 comments takes <10ms.

## Out of Scope

- Real-time analytics streaming (WebSocket-based live updating of analytics)
- Cross-session hourly pattern analysis ("best time to go live")
- NLP-based keyword extraction (underthesea, pyvi)
- CSV/PDF export
- Response time tracking (no timestamp for when reply was generated)
- Pre-computed aggregate tables
- Caching layer
