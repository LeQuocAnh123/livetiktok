# Deep Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add intra-session activity timelines, trending keywords, engagement/conversion metrics, and a session detail page — all computed on read from existing data.

**Architecture:** Compute on read from `MessageLog` + `GiftLog` tables. Two new Python modules handle keyword extraction (regex + Vietnamese stopwords) and timeline bucketing (5-min intervals). Two API changes: enhance existing overview endpoint with 3 new fields, add new session detail endpoint. Frontend uses Recharts for all new charts.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, aiosqlite | Next.js 16, React 19, Recharts, shadcn/ui, Tailwind CSS

---

## File Structure

### New files
| File | Responsibility |
|---|---|
| `backend/app/core/analytics/__init__.py` | Package init |
| `backend/app/core/analytics/keywords.py` | Keyword extraction (regex tokenize + Vietnamese stopwords) |
| `backend/app/core/analytics/timeline.py` | Time-bucketing (5-min intervals) |
| `backend/tests/test_keywords.py` | Unit tests for keyword extraction |
| `backend/tests/test_timeline.py` | Unit tests for timeline bucketing |
| `backend/tests/test_session_analytics_api.py` | Integration tests for session detail endpoint |
| `frontend/components/analytics/SentimentTrend.tsx` | Recharts AreaChart — daily sentiment trend |
| `frontend/components/analytics/KeywordCloud.tsx` | Recharts horizontal BarChart — top keywords |
| `frontend/components/analytics/SessionList.tsx` | Table — session list with drilldown |
| `frontend/components/analytics/ActivityTimeline.tsx` | Recharts ComposedChart — intra-session timeline |
| `frontend/components/analytics/SentimentBreakdown.tsx` | Recharts PieChart — sentiment breakdown |
| `frontend/components/analytics/EngagementMetrics.tsx` | KPI cards — engagement + proxy conversion |
| `frontend/app/analytics/sessions/[id]/page.tsx` | Session detail page |

### Modified files
| File | Changes |
|---|---|
| `backend/app/schemas/analytics.py` | Add ~10 new Pydantic models, extend `AnalyticsResponse` |
| `backend/app/api/v1/analytics.py` | Enhance overview endpoint + add session detail endpoint |
| `backend/tests/test_analytics_api.py` | Add tests for enhanced overview fields |
| `frontend/lib/api.ts` | Add types + `api.analytics.session()` method |
| `frontend/app/analytics/page.tsx` | Add SentimentTrend, KeywordCloud, SessionList sections |

---

## Task 1: Keyword Extraction Module (TDD)

**Files:**
- Create: `backend/app/core/analytics/__init__.py`
- Create: `backend/app/core/analytics/keywords.py`
- Create: `backend/tests/test_keywords.py`

- [ ] **Step 1: Create analytics package init**

```bash
mkdir -p backend/app/core/analytics
```

Create `backend/app/core/analytics/__init__.py`:

```python
```

(Empty file — just makes it a package.)

- [ ] **Step 2: Write failing tests for `extract_keywords`**

Create `backend/tests/test_keywords.py`:

```python
"""Unit tests for keyword extraction."""

import pytest

from app.core.analytics.keywords import extract_keywords


class TestExtractKeywords:
    def test_returns_top_keywords_sorted_by_count(self):
        comments = [
            "giá bao nhiêu",
            "giá sản phẩm này",
            "giao hàng nhanh không",
            "giá rẻ quá",
            "hàng đẹp",
        ]
        result = extract_keywords(comments, top_n=3)
        assert len(result) == 3
        assert result[0]["word"] == "giá"
        assert result[0]["count"] == 3
        # Each entry has word + count keys
        for entry in result:
            assert "word" in entry
            assert "count" in entry

    def test_filters_vietnamese_stopwords(self):
        comments = [
            "của tôi là cái này",
            "được không vậy",
            "sản phẩm đẹp lắm",
        ]
        result = extract_keywords(comments, top_n=20)
        words = [e["word"] for e in result]
        # Common stopwords should not appear
        for sw in ["của", "là", "này", "được", "không", "vậy"]:
            assert sw not in words

    def test_empty_input_returns_empty_list(self):
        assert extract_keywords([], top_n=10) == []

    def test_filters_single_char_words(self):
        comments = ["a b c sản phẩm"]
        result = extract_keywords(comments, top_n=10)
        words = [e["word"] for e in result]
        assert "a" not in words
        assert "b" not in words
        assert "c" not in words

    def test_case_insensitive(self):
        comments = ["Giá bao nhiêu", "giá rẻ", "GIÁ tốt"]
        result = extract_keywords(comments, top_n=1)
        assert result[0]["word"] == "giá"
        assert result[0]["count"] == 3

    def test_top_n_limits_results(self):
        comments = ["từ1 từ2 từ3 từ4 từ5 từ6 từ7 từ8 từ9 từ10"]
        result = extract_keywords(comments, top_n=5)
        assert len(result) <= 5

    def test_handles_punctuation(self):
        comments = ["giá? giá! giá..."]
        result = extract_keywords(comments, top_n=1)
        assert result[0]["word"] == "giá"
        assert result[0]["count"] == 3
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_keywords.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.analytics.keywords'`

- [ ] **Step 4: Implement `extract_keywords`**

Create `backend/app/core/analytics/keywords.py`:

```python
"""Keyword extraction from comment lists.

Uses regex tokenization + Vietnamese stopword filtering.
No external NLP dependencies.
"""

import re
from collections import Counter

# ~120 common Vietnamese stopwords (function words, particles, TikTok filler)
VIETNAMESE_STOPWORDS: frozenset[str] = frozenset({
    # Pronouns
    "tôi", "tao", "mình", "chúng", "ta", "bạn", "cậu", "anh", "chị", "em",
    "ông", "bà", "nó", "họ", "ai", "gì",
    # Conjunctions & prepositions
    "và", "hoặc", "hay", "nhưng", "mà", "với", "của", "cho", "từ", "trong",
    "trên", "dưới", "ngoài", "về", "theo", "bằng", "để", "tới", "đến",
    # Particles & modifiers
    "là", "có", "không", "đã", "đang", "sẽ", "được", "bị", "phải", "cần",
    "nên", "thì", "cũng", "vẫn", "còn", "rất", "lắm", "quá", "hơn",
    "nhất", "này", "đó", "kia", "ấy", "nào", "mỗi", "các", "những",
    "một", "hai", "ba", "tất", "cả", "mọi",
    # Question words
    "sao", "nào", "đâu", "bao",
    # TikTok filler words
    "ạ", "nha", "nhé", "ơi", "vậy", "nhỉ", "hen", "nè", "luôn", "nghen",
    "dạ", "vâng", "ừ", "ờ", "à", "ồ",
    # Common verbs that are too generic
    "làm", "biết", "nói", "xem", "cho", "lấy", "đi", "đến", "ra", "vào",
    "lên", "xuống",
    # Other function words
    "thế", "rồi", "đây", "khi", "nếu", "vì", "do", "tại", "lại", "chỉ",
    "mới", "ngay", "thôi", "hết", "xong",
})

_TOKEN_RE = re.compile(r"[a-zA-ZÀ-ỹ0-9]+", re.UNICODE)


def extract_keywords(
    comments: list[str], top_n: int = 20
) -> list[dict[str, int | str]]:
    """Extract top keywords from a list of comment strings.

    Process:
    1. Lowercase + normalize
    2. Tokenize: regex split on non-word characters
    3. Filter: remove stopwords, words < 2 chars
    4. Count frequency
    5. Return top_n as [{"word": "giá", "count": 45}, ...]
    """
    if not comments:
        return []

    counter: Counter[str] = Counter()

    for comment in comments:
        tokens = _TOKEN_RE.findall(comment.lower())
        for token in tokens:
            if len(token) >= 2 and token not in VIETNAMESE_STOPWORDS:
                counter[token] += 1

    return [
        {"word": word, "count": count}
        for word, count in counter.most_common(top_n)
    ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_keywords.py -v`

Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/analytics/__init__.py backend/app/core/analytics/keywords.py backend/tests/test_keywords.py
git commit -m "feat(analytics): add keyword extraction module with Vietnamese stopwords"
```

---

## Task 2: Timeline Bucketing Module (TDD)

**Files:**
- Create: `backend/app/core/analytics/timeline.py`
- Create: `backend/tests/test_timeline.py`

- [ ] **Step 1: Write failing tests for `compute_timeline`**

Create `backend/tests/test_timeline.py`:

```python
"""Unit tests for timeline bucketing."""

from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest

from app.core.analytics.timeline import TimelineBucket, compute_timeline


def _make_msg(created_at: datetime, reply: str | None = "reply"):
    """Create a minimal message-like object for testing."""
    class FakeMsg:
        pass
    m = FakeMsg()
    m.created_at = created_at
    m.reply = reply
    return m


def _make_gift(created_at: datetime, total_diamonds: int = 10):
    """Create a minimal gift-like object for testing."""
    class FakeGift:
        pass
    g = FakeGift()
    g.created_at = created_at
    g.total_diamonds = total_diamonds
    return g


class TestComputeTimeline:
    def test_single_bucket_for_short_session(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 10, 4, 0)  # 4 minutes
        msgs = [_make_msg(start + timedelta(minutes=1))]
        gifts = [_make_gift(start + timedelta(minutes=2), total_diamonds=50)]

        result = compute_timeline(start, end, msgs, gifts, bucket_minutes=5)

        assert len(result) == 1
        assert result[0].comment_count == 1
        assert result[0].gift_count == 1
        assert result[0].gift_diamonds == 50

    def test_multiple_buckets(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 10, 12, 0)  # 12 minutes -> 3 buckets
        msgs = [
            _make_msg(start + timedelta(minutes=1)),  # bucket 0
            _make_msg(start + timedelta(minutes=3)),  # bucket 0
            _make_msg(start + timedelta(minutes=7)),  # bucket 1
        ]
        gifts = [
            _make_gift(start + timedelta(minutes=11), total_diamonds=100),  # bucket 2
        ]

        result = compute_timeline(start, end, msgs, gifts, bucket_minutes=5)

        assert len(result) == 3
        assert result[0].comment_count == 2
        assert result[1].comment_count == 1
        assert result[2].comment_count == 0
        assert result[2].gift_count == 1
        assert result[2].gift_diamonds == 100

    def test_empty_session(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 10, 10, 0)

        result = compute_timeline(start, end, [], [], bucket_minutes=5)

        assert len(result) == 2
        for b in result:
            assert b.comment_count == 0
            assert b.reply_count == 0
            assert b.gift_count == 0
            assert b.gift_diamonds == 0

    def test_session_without_end_uses_last_event(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        last_msg_time = datetime(2026, 1, 1, 10, 8, 0)
        msgs = [_make_msg(last_msg_time)]

        result = compute_timeline(start, None, msgs, [], bucket_minutes=5)

        # Should span from start to last event: 8 minutes -> 2 buckets
        assert len(result) == 2
        assert result[1].comment_count == 1

    def test_session_without_end_and_no_events(self):
        start = datetime(2026, 1, 1, 10, 0, 0)

        result = compute_timeline(start, None, [], [], bucket_minutes=5)

        # No end, no events -> 1 default bucket
        assert len(result) == 1
        assert result[0].comment_count == 0

    def test_reply_count_tracks_messages_with_reply(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 10, 5, 0)
        msgs = [
            _make_msg(start + timedelta(minutes=1), reply="answered"),
            _make_msg(start + timedelta(minutes=2), reply=None),  # unanswered
            _make_msg(start + timedelta(minutes=3), reply="answered"),
        ]

        result = compute_timeline(start, end, msgs, [], bucket_minutes=5)

        assert result[0].comment_count == 3
        assert result[0].reply_count == 2

    def test_bucket_boundaries(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 10, 10, 0)

        result = compute_timeline(start, end, [], [], bucket_minutes=5)

        assert result[0].bucket_start == start
        assert result[0].bucket_end == start + timedelta(minutes=5)
        assert result[1].bucket_start == start + timedelta(minutes=5)
        assert result[1].bucket_end == start + timedelta(minutes=10)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_timeline.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.analytics.timeline'`

- [ ] **Step 3: Implement `compute_timeline`**

Create `backend/app/core/analytics/timeline.py`:

```python
"""Time-bucketed activity computation for live sessions.

Bucketing done in Python (not SQL) because SQLite date/time
functions are limited and data fits comfortably in memory.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import math


@dataclass
class TimelineBucket:
    bucket_start: datetime
    bucket_end: datetime
    comment_count: int = 0
    reply_count: int = 0
    gift_count: int = 0
    gift_diamonds: int = 0


def compute_timeline(
    session_start: datetime,
    session_end: datetime | None,
    messages: list,
    gifts: list,
    bucket_minutes: int = 5,
) -> list[TimelineBucket]:
    """Compute time-bucketed activity for a session.

    Args:
        session_start: When the live session started.
        session_end: When the session ended (None if still active).
        messages: MessageLog rows (need .created_at, .reply attributes).
        gifts: GiftLog rows (need .created_at, .total_diamonds attributes).
        bucket_minutes: Width of each bucket in minutes.

    Returns:
        Sorted list of TimelineBucket objects.
    """
    bucket_seconds = bucket_minutes * 60

    # Determine effective end time
    effective_end = session_end
    if effective_end is None:
        # Use the latest event time, or session_start + 1 bucket as fallback
        event_times: list[datetime] = []
        for m in messages:
            event_times.append(m.created_at)
        for g in gifts:
            event_times.append(g.created_at)

        if event_times:
            effective_end = max(event_times)
        else:
            effective_end = session_start + timedelta(seconds=bucket_seconds)

    # Calculate number of buckets
    total_seconds = (effective_end - session_start).total_seconds()
    num_buckets = max(1, math.ceil(total_seconds / bucket_seconds))

    # Create empty buckets
    buckets: list[TimelineBucket] = []
    for i in range(num_buckets):
        b_start = session_start + timedelta(seconds=i * bucket_seconds)
        b_end = session_start + timedelta(seconds=(i + 1) * bucket_seconds)
        buckets.append(TimelineBucket(bucket_start=b_start, bucket_end=b_end))

    # Assign messages to buckets
    for msg in messages:
        offset = (msg.created_at - session_start).total_seconds()
        idx = min(int(offset // bucket_seconds), num_buckets - 1)
        if idx < 0:
            idx = 0
        buckets[idx].comment_count += 1
        if msg.reply is not None:
            buckets[idx].reply_count += 1

    # Assign gifts to buckets
    for gift in gifts:
        offset = (gift.created_at - session_start).total_seconds()
        idx = min(int(offset // bucket_seconds), num_buckets - 1)
        if idx < 0:
            idx = 0
        buckets[idx].gift_count += 1
        buckets[idx].gift_diamonds += gift.total_diamonds

    return buckets
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_timeline.py -v`

Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/analytics/timeline.py backend/tests/test_timeline.py
git commit -m "feat(analytics): add timeline bucketing module for intra-session activity"
```

---

## Task 3: New Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas/analytics.py`

- [ ] **Step 1: Add new schema models and extend `AnalyticsResponse`**

Replace the entire file `backend/app/schemas/analytics.py` with:

```python
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.gift import GiftStats


# ── Session detail schemas ────────────────────────────────────────────────────


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


class TimelineBucketSchema(BaseModel):
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
    product_inquiry_rate: float  # percentage
    unique_commenters: int
    comments_per_minute_avg: float
    peak_minute: datetime | None
    peak_comments: int


class SessionAnalyticsResponse(BaseModel):
    session_info: SessionInfo
    summary: SessionSummary
    timeline: list[TimelineBucketSchema]
    top_keywords: list[KeywordEntry]
    intent_breakdown: dict[str, int]
    sentiment_breakdown: dict[str, int]
    engagement_metrics: EngagementMetrics


# ── Enhanced overview schemas ─────────────────────────────────────────────────


class SentimentTrendEntry(BaseModel):
    date: str  # "YYYY-MM-DD"
    positive: int = 0
    neutral: int = 0
    negative: int = 0


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


# ── Main overview response (extended) ─────────────────────────────────────────


class AnalyticsResponse(BaseModel):
    total_sessions: int
    total_comments: int
    total_replies: int
    reply_rate: float  # 0-100
    intent_breakdown: dict[str, int] = Field(
        default_factory=dict, description="Intent label to count mapping"
    )
    sentiment_breakdown: dict[str, int] = Field(
        default_factory=dict, description="Sentiment label to count mapping"
    )
    unanswered_count: int
    gift_stats: GiftStats | None = None
    # New fields for deep analytics
    sentiment_trend: list[SentimentTrendEntry] = Field(default_factory=list)
    top_keywords_overall: list[KeywordEntry] = Field(default_factory=list)
    session_list: list[SessionListEntry] = Field(default_factory=list)
```

- [ ] **Step 2: Run existing tests to verify nothing breaks**

Run: `python3 -m pytest backend/tests/test_analytics_api.py -v`

Expected: All existing tests still PASS (new fields have defaults so backward compatible)

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/analytics.py
git commit -m "feat(analytics): add Pydantic schemas for deep analytics"
```

---

## Task 4: Enhance Overview Endpoint (TDD)

**Files:**
- Modify: `backend/tests/test_analytics_api.py`
- Modify: `backend/app/api/v1/analytics.py`

- [ ] **Step 1: Write failing tests for new overview fields**

Add the following tests at the end of `backend/tests/test_analytics_api.py`:

```python
from datetime import datetime, timedelta
from app.models.session import LiveSession
from app.models.message import MessageLog
from app.models.gift import GiftLog


async def test_overview_includes_sentiment_trend(auth_client: AsyncClient, db_session, test_seller):
    """Enhanced overview returns sentiment_trend as daily aggregation."""
    # Create session + messages with different sentiments on different days
    session = LiveSession(
        id="sess-trend-1",
        seller_id=test_seller.id,
        started_at=datetime(2026, 1, 1, 10, 0),
        ended_at=datetime(2026, 1, 1, 12, 0),
    )
    db_session.add(session)

    msgs = [
        MessageLog(
            id="mt1", session_id="sess-trend-1", user_unique_id="u1",
            comment="great", reply="thanks", intent="greeting", sentiment="positive",
            created_at=datetime(2026, 1, 1, 10, 5),
        ),
        MessageLog(
            id="mt2", session_id="sess-trend-1", user_unique_id="u2",
            comment="ok", reply="hi", intent="greeting", sentiment="neutral",
            created_at=datetime(2026, 1, 1, 10, 10),
        ),
        MessageLog(
            id="mt3", session_id="sess-trend-1", user_unique_id="u3",
            comment="bad", reply="sorry", intent="unknown", sentiment="negative",
            created_at=datetime(2026, 1, 1, 10, 15),
        ),
    ]
    db_session.add_all(msgs)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()

    assert "sentiment_trend" in data
    assert len(data["sentiment_trend"]) == 1  # all same day
    day = data["sentiment_trend"][0]
    assert day["date"] == "2026-01-01"
    assert day["positive"] == 1
    assert day["neutral"] == 1
    assert day["negative"] == 1


async def test_overview_includes_top_keywords(auth_client: AsyncClient, db_session, test_seller):
    """Enhanced overview returns top_keywords_overall."""
    session = LiveSession(
        id="sess-kw-1",
        seller_id=test_seller.id,
        started_at=datetime(2026, 1, 1, 10, 0),
        ended_at=datetime(2026, 1, 1, 12, 0),
    )
    db_session.add(session)

    msgs = [
        MessageLog(
            id="mk1", session_id="sess-kw-1", user_unique_id="u1",
            comment="giá bao nhiêu", reply="100k", intent="product_inquiry", sentiment="neutral",
            created_at=datetime(2026, 1, 1, 10, 5),
        ),
        MessageLog(
            id="mk2", session_id="sess-kw-1", user_unique_id="u2",
            comment="giá sản phẩm", reply="200k", intent="product_inquiry", sentiment="neutral",
            created_at=datetime(2026, 1, 1, 10, 10),
        ),
    ]
    db_session.add_all(msgs)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()

    assert "top_keywords_overall" in data
    assert len(data["top_keywords_overall"]) > 0
    # "giá" appears in both comments
    words = [kw["word"] for kw in data["top_keywords_overall"]]
    assert "giá" in words


async def test_overview_includes_session_list(auth_client: AsyncClient, db_session, test_seller):
    """Enhanced overview returns session_list with per-session summaries."""
    session = LiveSession(
        id="sess-list-1",
        seller_id=test_seller.id,
        started_at=datetime(2026, 1, 1, 10, 0),
        ended_at=datetime(2026, 1, 1, 11, 30),
    )
    db_session.add(session)

    msgs = [
        MessageLog(
            id="ml1", session_id="sess-list-1", user_unique_id="u1",
            comment="giá bao nhiêu", reply="100k", intent="product_inquiry", sentiment="positive",
            created_at=datetime(2026, 1, 1, 10, 5),
        ),
        MessageLog(
            id="ml2", session_id="sess-list-1", user_unique_id="u2",
            comment="chào shop", reply=None, intent="greeting", sentiment="neutral",
            created_at=datetime(2026, 1, 1, 10, 10),
        ),
    ]
    gift = GiftLog(
        id="gl1", session_id="sess-list-1", user_unique_id="u1",
        gift_name="Rose", diamond_count=1, repeat_count=5,
        total_diamonds=5, estimated_usd=0.025,
        created_at=datetime(2026, 1, 1, 10, 20),
    )
    db_session.add_all(msgs)
    db_session.add(gift)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()

    assert "session_list" in data
    assert len(data["session_list"]) == 1
    s = data["session_list"][0]
    assert s["id"] == "sess-list-1"
    assert s["comment_count"] == 2
    assert s["reply_count"] == 1
    assert s["reply_rate"] == 50.0
    assert s["gift_count"] == 1
    assert s["gift_diamonds"] == 5
    assert s["top_intent"] == "product_inquiry"
    assert s["duration_minutes"] == 90.0


async def test_overview_new_fields_default_empty(auth_client: AsyncClient, test_seller):
    """New fields return empty lists when no data."""
    resp = await auth_client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["sentiment_trend"] == []
    assert data["top_keywords_overall"] == []
    assert data["session_list"] == []
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python3 -m pytest backend/tests/test_analytics_api.py -v`

Expected: New tests FAIL (the response doesn't include the new fields yet). The existing `test_analytics_returns_zeros_for_new_seller` may also fail because the response now includes extra fields — that's expected and will be fixed in the implementation.

- [ ] **Step 3: Implement enhanced overview endpoint**

Modify `backend/app/api/v1/analytics.py`. Replace the entire file with:

```python
"""Analytics API — aggregated stats for a seller."""

from collections import Counter
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_seller
from app.core.analytics.keywords import extract_keywords
from app.core.analytics.timeline import compute_timeline
from app.database import get_db
from app.models.gift import GiftLog
from app.models.message import MessageLog
from app.models.seller import Seller
from app.models.session import LiveSession
from app.schemas.analytics import (
    AnalyticsResponse,
    EngagementMetrics,
    KeywordEntry,
    SessionAnalyticsResponse,
    SessionInfo,
    SessionListEntry,
    SessionSummary,
    SentimentTrendEntry,
    TimelineBucketSchema,
)
from app.schemas.gift import GiftBreakdown, GiftStats, TopGifter

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    start_date: date | None = Query(
        default=None, description="Filter sessions from this date (inclusive)"
    ),
    end_date: date | None = Query(
        default=None, description="Filter sessions until this date (inclusive)"
    ),
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
):
    seller_id = current_seller.id

    # Base session filter
    session_filter = LiveSession.seller_id == seller_id

    # Add date filters if provided
    if start_date:
        start_datetime = datetime.combine(start_date, time.min)
        session_filter = session_filter & (LiveSession.started_at >= start_datetime)
    if end_date:
        end_datetime = datetime.combine(end_date, time.max)
        session_filter = session_filter & (LiveSession.started_at <= end_datetime)

    total_sessions = await db.scalar(select(func.count(LiveSession.id)).where(session_filter)) or 0

    session_subquery = select(LiveSession.id).where(session_filter).scalar_subquery()

    total_comments = (
        await db.scalar(
            select(func.count(MessageLog.id)).where(MessageLog.session_id.in_(session_subquery))
        )
        or 0
    )

    total_replies = (
        await db.scalar(
            select(func.count(MessageLog.id)).where(
                MessageLog.session_id.in_(session_subquery),
                MessageLog.reply.isnot(None),
            )
        )
        or 0
    )

    reply_rate = round((total_replies / total_comments * 100), 1) if total_comments > 0 else 0.0

    intent_rows = await db.execute(
        select(MessageLog.intent, func.count(MessageLog.id))
        .where(MessageLog.session_id.in_(session_subquery))
        .group_by(MessageLog.intent)
    )
    intent_breakdown = {row[0]: row[1] for row in intent_rows.all()}

    sentiment_rows = await db.execute(
        select(MessageLog.sentiment, func.count(MessageLog.id))
        .where(MessageLog.session_id.in_(session_subquery))
        .group_by(MessageLog.sentiment)
    )
    sentiment_breakdown = {row[0]: row[1] for row in sentiment_rows.all()}

    unanswered_count = (
        await db.scalar(
            select(func.count(MessageLog.id)).where(
                MessageLog.session_id.in_(session_subquery),
                MessageLog.reply.is_(None),
                MessageLog.intent.notin_(["skipped", "blacklist"]),
            )
        )
        or 0
    )

    # Gift stats
    gift_session_subquery = select(LiveSession.id).where(session_filter).scalar_subquery()

    total_gifts = (
        await db.scalar(
            select(func.count(GiftLog.id)).where(GiftLog.session_id.in_(gift_session_subquery))
        )
        or 0
    )

    total_diamonds = (
        await db.scalar(
            select(func.coalesce(func.sum(GiftLog.total_diamonds), 0)).where(
                GiftLog.session_id.in_(gift_session_subquery)
            )
        )
        or 0
    )

    total_gift_usd = (
        await db.scalar(
            select(func.coalesce(func.sum(GiftLog.estimated_usd), 0.0)).where(
                GiftLog.session_id.in_(gift_session_subquery)
            )
        )
        or 0.0
    )

    # Top gifters (top 5 by total diamonds)
    top_gifter_rows = await db.execute(
        select(
            GiftLog.user_unique_id,
            func.sum(GiftLog.total_diamonds).label("sum_diamonds"),
            func.count(GiftLog.id).label("gift_count"),
        )
        .where(GiftLog.session_id.in_(gift_session_subquery))
        .group_by(GiftLog.user_unique_id)
        .order_by(func.sum(GiftLog.total_diamonds).desc())
        .limit(5)
    )
    top_gifters = [
        TopGifter(user=row[0], total_diamonds=int(row[1]), gift_count=int(row[2]))
        for row in top_gifter_rows.all()
    ]

    # Gift breakdown by gift type
    gift_breakdown_rows = await db.execute(
        select(
            GiftLog.gift_name,
            func.count(GiftLog.id).label("count"),
            func.sum(GiftLog.total_diamonds).label("sum_diamonds"),
        )
        .where(GiftLog.session_id.in_(gift_session_subquery))
        .group_by(GiftLog.gift_name)
        .order_by(func.sum(GiftLog.total_diamonds).desc())
    )
    gift_breakdown = [
        GiftBreakdown(gift_name=row[0], count=int(row[1]), total_diamonds=int(row[2]))
        for row in gift_breakdown_rows.all()
    ]

    gift_stats = GiftStats(
        total_gifts=total_gifts,
        total_diamonds=int(total_diamonds),
        estimated_usd=float(total_gift_usd),
        top_gifters=top_gifters,
        gift_breakdown=gift_breakdown,
    )

    # ── NEW: Sentiment trend (daily aggregation) ──────────────────────────────
    sentiment_trend_rows = await db.execute(
        select(
            func.strftime("%Y-%m-%d", MessageLog.created_at).label("day"),
            MessageLog.sentiment,
            func.count(MessageLog.id),
        )
        .where(MessageLog.session_id.in_(session_subquery))
        .group_by("day", MessageLog.sentiment)
        .order_by("day")
    )

    # Pivot into {date: {positive: N, neutral: N, negative: N}}
    trend_map: dict[str, dict[str, int]] = {}
    for day_str, sentiment, cnt in sentiment_trend_rows.all():
        if day_str not in trend_map:
            trend_map[day_str] = {"positive": 0, "neutral": 0, "negative": 0}
        if sentiment in trend_map[day_str]:
            trend_map[day_str][sentiment] = cnt

    sentiment_trend = [
        SentimentTrendEntry(date=d, **counts)
        for d, counts in sorted(trend_map.items())
    ]

    # ── NEW: Top keywords overall ─────────────────────────────────────────────
    comment_rows = await db.execute(
        select(MessageLog.comment).where(MessageLog.session_id.in_(session_subquery))
    )
    all_comments = [row[0] for row in comment_rows.all()]
    kw_results = extract_keywords(all_comments, top_n=20)
    top_keywords_overall = [KeywordEntry(**kw) for kw in kw_results]

    # ── NEW: Session list (per-session summaries) ─────────────────────────────
    sessions_result = await db.execute(
        select(LiveSession).where(session_filter).order_by(LiveSession.started_at.desc())
    )
    sessions = sessions_result.scalars().all()

    session_list: list[SessionListEntry] = []
    for sess in sessions:
        s_msg_rows = await db.execute(
            select(
                func.count(MessageLog.id),
                func.count(MessageLog.reply),
            ).where(MessageLog.session_id == sess.id)
        )
        s_msg = s_msg_rows.one()
        s_comment_count = s_msg[0]
        s_reply_count = s_msg[1]

        s_intent_rows = await db.execute(
            select(MessageLog.intent, func.count(MessageLog.id))
            .where(MessageLog.session_id == sess.id)
            .group_by(MessageLog.intent)
            .order_by(func.count(MessageLog.id).desc())
            .limit(1)
        )
        s_top_intent_row = s_intent_rows.first()
        s_top_intent = s_top_intent_row[0] if s_top_intent_row else "none"

        s_gift_rows = await db.execute(
            select(
                func.count(GiftLog.id),
                func.coalesce(func.sum(GiftLog.total_diamonds), 0),
            ).where(GiftLog.session_id == sess.id)
        )
        s_gift = s_gift_rows.one()

        duration_minutes = 0.0
        if sess.ended_at and sess.started_at:
            duration_minutes = round(
                (sess.ended_at - sess.started_at).total_seconds() / 60, 1
            )

        s_reply_rate = (
            round(s_reply_count / s_comment_count * 100, 1) if s_comment_count > 0 else 0.0
        )

        session_list.append(
            SessionListEntry(
                id=sess.id,
                started_at=sess.started_at,
                ended_at=sess.ended_at,
                duration_minutes=duration_minutes,
                comment_count=s_comment_count,
                reply_count=s_reply_count,
                reply_rate=s_reply_rate,
                gift_count=s_gift[0],
                gift_diamonds=int(s_gift[1]),
                top_intent=s_top_intent,
            )
        )

    return AnalyticsResponse(
        total_sessions=total_sessions,
        total_comments=total_comments,
        total_replies=total_replies,
        reply_rate=reply_rate,
        intent_breakdown=intent_breakdown,
        sentiment_breakdown=sentiment_breakdown,
        unanswered_count=unanswered_count,
        gift_stats=gift_stats,
        sentiment_trend=sentiment_trend,
        top_keywords_overall=top_keywords_overall,
        session_list=session_list,
    )
```

**Note on `func.count(MessageLog.reply)`:** SQLAlchemy's `func.count(column)` counts non-NULL values only (like SQL `COUNT(col)`), so this correctly counts messages that have a reply.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_analytics_api.py -v`

Expected: All tests PASS (both existing and new)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/analytics.py backend/tests/test_analytics_api.py
git commit -m "feat(analytics): enhance overview with sentiment trend, keywords, session list"
```

---

## Task 5: Session Detail Endpoint (TDD)

**Files:**
- Create: `backend/tests/test_session_analytics_api.py`
- Modify: `backend/app/api/v1/analytics.py` (add new endpoint below existing)

- [ ] **Step 1: Write failing tests for session detail endpoint**

Create `backend/tests/test_session_analytics_api.py`:

```python
"""Integration tests for session detail analytics endpoint."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.gift import GiftLog
from app.models.message import MessageLog
from app.models.session import LiveSession


async def test_session_detail_returns_full_analytics(
    auth_client: AsyncClient, db_session, test_seller
):
    """GET /api/v1/analytics/sessions/{id} returns complete analytics."""
    session = LiveSession(
        id="sess-detail-1",
        seller_id=test_seller.id,
        started_at=datetime(2026, 1, 1, 10, 0),
        ended_at=datetime(2026, 1, 1, 10, 30),
    )
    db_session.add(session)

    msgs = [
        MessageLog(
            id="sd1", session_id="sess-detail-1", user_unique_id="u1",
            comment="giá bao nhiêu", reply="100k ạ", intent="product_inquiry",
            sentiment="neutral", created_at=datetime(2026, 1, 1, 10, 2),
        ),
        MessageLog(
            id="sd2", session_id="sess-detail-1", user_unique_id="u2",
            comment="chào shop", reply="chào bạn", intent="greeting",
            sentiment="positive", created_at=datetime(2026, 1, 1, 10, 7),
        ),
        MessageLog(
            id="sd3", session_id="sess-detail-1", user_unique_id="u3",
            comment="giá sản phẩm này", reply=None, intent="product_inquiry",
            sentiment="neutral", created_at=datetime(2026, 1, 1, 10, 12),
        ),
    ]
    gift = GiftLog(
        id="sg1", session_id="sess-detail-1", user_unique_id="u1",
        gift_name="Rose", diamond_count=1, repeat_count=10,
        total_diamonds=10, estimated_usd=0.05,
        created_at=datetime(2026, 1, 1, 10, 5),
    )
    db_session.add_all(msgs)
    db_session.add(gift)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/sessions/sess-detail-1")
    assert resp.status_code == 200
    data = resp.json()

    # session_info
    assert data["session_info"]["id"] == "sess-detail-1"
    assert data["session_info"]["duration_minutes"] == 30.0

    # summary
    assert data["summary"]["total_comments"] == 3
    assert data["summary"]["total_replies"] == 2
    assert data["summary"]["reply_rate"] == 66.7
    assert data["summary"]["total_gifts"] == 1
    assert data["summary"]["total_diamonds"] == 10
    assert data["summary"]["estimated_usd"] == 0.05

    # timeline (30 min / 5 min = 6 buckets)
    assert len(data["timeline"]) == 6

    # keywords
    assert len(data["top_keywords"]) > 0
    words = [kw["word"] for kw in data["top_keywords"]]
    assert "giá" in words

    # breakdowns
    assert data["intent_breakdown"]["product_inquiry"] == 2
    assert data["intent_breakdown"]["greeting"] == 1
    assert data["sentiment_breakdown"]["neutral"] == 2
    assert data["sentiment_breakdown"]["positive"] == 1

    # engagement
    assert data["engagement_metrics"]["product_inquiry_rate"] == pytest.approx(66.7, abs=0.1)
    assert data["engagement_metrics"]["unique_commenters"] == 3


async def test_session_detail_404_for_nonexistent(auth_client: AsyncClient, test_seller):
    """Returns 404 for a session that doesn't exist."""
    resp = await auth_client.get("/api/v1/analytics/sessions/nonexistent-id")
    assert resp.status_code == 404


async def test_session_detail_403_for_other_seller(
    auth_client: AsyncClient, db_session, test_seller
):
    """Returns 403 for a session belonging to another seller."""
    session = LiveSession(
        id="sess-other-1",
        seller_id="other-seller-id",
        started_at=datetime(2026, 1, 1, 10, 0),
    )
    db_session.add(session)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/sessions/sess-other-1")
    assert resp.status_code == 403


async def test_session_detail_empty_session(auth_client: AsyncClient, db_session, test_seller):
    """Returns empty timeline and zero stats for session with no messages."""
    session = LiveSession(
        id="sess-empty-1",
        seller_id=test_seller.id,
        started_at=datetime(2026, 1, 1, 10, 0),
        ended_at=datetime(2026, 1, 1, 10, 10),
    )
    db_session.add(session)
    await db_session.commit()

    resp = await auth_client.get("/api/v1/analytics/sessions/sess-empty-1")
    assert resp.status_code == 200
    data = resp.json()

    assert data["summary"]["total_comments"] == 0
    assert data["summary"]["total_replies"] == 0
    assert data["summary"]["reply_rate"] == 0.0
    assert data["summary"]["total_gifts"] == 0
    assert len(data["timeline"]) == 2  # 10 min / 5 min = 2 buckets
    assert data["top_keywords"] == []
    assert data["engagement_metrics"]["unique_commenters"] == 0
    assert data["engagement_metrics"]["peak_minute"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_session_analytics_api.py -v`

Expected: FAIL with 404 (endpoint doesn't exist yet)

- [ ] **Step 3: Implement session detail endpoint**

Add the following to the **end** of `backend/app/api/v1/analytics.py` (after the existing `get_analytics` function):

```python


@router.get("/sessions/{session_id}", response_model=SessionAnalyticsResponse)
async def get_session_analytics(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
):
    """Get detailed analytics for a single live session."""
    # 1. Fetch session and verify ownership
    session = await db.get(LiveSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.seller_id != current_seller.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # 2. Fetch all messages for this session
    msg_result = await db.execute(
        select(MessageLog).where(MessageLog.session_id == session_id)
    )
    messages = msg_result.scalars().all()

    # 3. Fetch all gifts for this session
    gift_result = await db.execute(
        select(GiftLog).where(GiftLog.session_id == session_id)
    )
    gifts = gift_result.scalars().all()

    # 4. Session info
    duration_minutes = 0.0
    if session.ended_at and session.started_at:
        duration_minutes = round(
            (session.ended_at - session.started_at).total_seconds() / 60, 1
        )

    session_info = SessionInfo(
        id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_minutes=duration_minutes,
    )

    # 5. Summary
    total_comments = len(messages)
    total_replies = sum(1 for m in messages if m.reply is not None)
    reply_rate = round(total_replies / total_comments * 100, 1) if total_comments > 0 else 0.0
    total_gifts = len(gifts)
    total_diamonds = sum(g.total_diamonds for g in gifts)
    estimated_usd = round(sum(g.estimated_usd for g in gifts), 2)

    summary = SessionSummary(
        total_comments=total_comments,
        total_replies=total_replies,
        reply_rate=reply_rate,
        total_gifts=total_gifts,
        total_diamonds=total_diamonds,
        estimated_usd=estimated_usd,
    )

    # 6. Timeline
    timeline_buckets = compute_timeline(
        session_start=session.started_at,
        session_end=session.ended_at,
        messages=messages,
        gifts=gifts,
        bucket_minutes=5,
    )
    timeline = [
        TimelineBucketSchema(
            bucket_start=b.bucket_start,
            bucket_end=b.bucket_end,
            comment_count=b.comment_count,
            reply_count=b.reply_count,
            gift_count=b.gift_count,
            gift_diamonds=b.gift_diamonds,
        )
        for b in timeline_buckets
    ]

    # 7. Keywords
    comment_texts = [m.comment for m in messages]
    kw_results = extract_keywords(comment_texts, top_n=20)
    top_keywords = [KeywordEntry(**kw) for kw in kw_results]

    # 8. Breakdowns
    intent_counter: dict[str, int] = {}
    sentiment_counter: dict[str, int] = {}
    for m in messages:
        intent_counter[m.intent] = intent_counter.get(m.intent, 0) + 1
        sentiment_counter[m.sentiment] = sentiment_counter.get(m.sentiment, 0) + 1

    # 9. Engagement metrics
    product_inquiry_count = intent_counter.get("product_inquiry", 0)
    product_inquiry_rate = (
        round(product_inquiry_count / total_comments * 100, 1) if total_comments > 0 else 0.0
    )

    unique_commenters = len({m.user_unique_id for m in messages})

    comments_per_minute_avg = 0.0
    if duration_minutes > 0:
        comments_per_minute_avg = round(total_comments / duration_minutes, 1)
    elif total_comments > 0 and messages:
        # Session still active — estimate from first to last message
        sorted_msgs = sorted(messages, key=lambda m: m.created_at)
        span = (sorted_msgs[-1].created_at - sorted_msgs[0].created_at).total_seconds() / 60
        if span > 0:
            comments_per_minute_avg = round(total_comments / span, 1)

    # Peak minute: find the minute with most comments
    peak_minute = None
    peak_comments = 0
    if messages:
        from collections import Counter

        minute_counts: Counter[str] = Counter()
        for m in messages:
            # Truncate to minute
            minute_key = m.created_at.replace(second=0, microsecond=0).isoformat()
            minute_counts[minute_key] += 1
        if minute_counts:
            peak_key, peak_comments = minute_counts.most_common(1)[0]
            peak_minute = datetime.fromisoformat(peak_key)

    engagement_metrics = EngagementMetrics(
        product_inquiry_rate=product_inquiry_rate,
        unique_commenters=unique_commenters,
        comments_per_minute_avg=comments_per_minute_avg,
        peak_minute=peak_minute,
        peak_comments=peak_comments,
    )

    return SessionAnalyticsResponse(
        session_info=session_info,
        summary=summary,
        timeline=timeline,
        top_keywords=top_keywords,
        intent_breakdown=intent_counter,
        sentiment_breakdown=sentiment_counter,
        engagement_metrics=engagement_metrics,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_session_analytics_api.py -v`

Expected: All 4 tests PASS

- [ ] **Step 5: Run the full backend test suite**

Run: `python3 -m pytest backend/tests/ -v`

Expected: All tests PASS (existing + new)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/analytics.py backend/tests/test_session_analytics_api.py
git commit -m "feat(analytics): add session detail endpoint with timeline, keywords, engagement"
```

---

## Task 6: Install Recharts

**Files:**
- Modify: `frontend/package.json` (via npm)

- [ ] **Step 1: Install recharts**

Run (from `frontend/` directory):

```bash
npm install recharts
```

- [ ] **Step 2: Verify installation**

Run: `node -e "require('recharts'); console.log('ok')"`

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: install recharts for analytics charts"
```

---

## Task 7: Frontend Types & API Client

**Files:**
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Add new TypeScript types and update `AnalyticsData`**

In `frontend/lib/api.ts`, add the following types after the existing `AnalyticsData` interface (after line 132):

```typescript
// Deep analytics types
export interface SentimentTrendEntry {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
}

export interface KeywordEntry {
  word: string;
  count: number;
}

export interface SessionListEntry {
  id: string;
  started_at: string;
  ended_at: string | null;
  duration_minutes: number;
  comment_count: number;
  reply_count: number;
  reply_rate: number;
  gift_count: number;
  gift_diamonds: number;
  top_intent: string;
}

export interface SessionInfo {
  id: string;
  started_at: string;
  ended_at: string | null;
  duration_minutes: number;
}

export interface SessionSummary {
  total_comments: number;
  total_replies: number;
  reply_rate: number;
  total_gifts: number;
  total_diamonds: number;
  estimated_usd: number;
}

export interface TimelineBucket {
  bucket_start: string;
  bucket_end: string;
  comment_count: number;
  reply_count: number;
  gift_count: number;
  gift_diamonds: number;
}

export interface EngagementMetrics {
  product_inquiry_rate: number;
  unique_commenters: number;
  comments_per_minute_avg: number;
  peak_minute: string | null;
  peak_comments: number;
}

export interface SessionAnalyticsData {
  session_info: SessionInfo;
  summary: SessionSummary;
  timeline: TimelineBucket[];
  top_keywords: KeywordEntry[];
  intent_breakdown: Record<string, number>;
  sentiment_breakdown: Record<string, number>;
  engagement_metrics: EngagementMetrics;
}
```

Then update the existing `AnalyticsData` interface (around line 123) to add the 3 new fields:

```typescript
export interface AnalyticsData {
  total_sessions: number;
  total_comments: number;
  total_replies: number;
  reply_rate: number;
  intent_breakdown: Record<string, number>;
  sentiment_breakdown: Record<string, number>;
  unanswered_count: number;
  gift_stats: GiftStats | null;
  // Deep analytics
  sentiment_trend: SentimentTrendEntry[];
  top_keywords_overall: KeywordEntry[];
  session_list: SessionListEntry[];
}
```

- [ ] **Step 2: Add `api.analytics.session()` method**

In the `api.analytics` section (around line 323), add the `session` method:

```typescript
  analytics: {
    get(params: { start_date?: string; end_date?: string } = {}): Promise<AnalyticsData> {
      return request(`/api/v1/analytics/${qs(params)}`, {
        method: "GET",
      });
    },

    session(sessionId: string): Promise<SessionAnalyticsData> {
      return request(`/api/v1/analytics/sessions/${sessionId}`, {
        method: "GET",
      });
    },
  },
```

- [ ] **Step 3: Verify TypeScript compiles**

Run (from `frontend/` directory): `npx tsc --noEmit`

Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat(analytics): add deep analytics types and session API method"
```

---

## Task 8: SentimentTrend Component

**Files:**
- Create: `frontend/components/analytics/SentimentTrend.tsx`

- [ ] **Step 1: Create the SentimentTrend component**

Create `frontend/components/analytics/SentimentTrend.tsx`:

```tsx
"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SentimentTrendEntry } from "@/lib/api";

interface Props {
  data: SentimentTrendEntry[];
}

export function SentimentTrend({ data }: Props) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Xu hướng cảm xúc</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Xu hướng cảm xúc</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Area
              type="monotone"
              dataKey="positive"
              name="Tích cực"
              stackId="1"
              stroke="#22c55e"
              fill="#22c55e"
              fillOpacity={0.6}
            />
            <Area
              type="monotone"
              dataKey="neutral"
              name="Trung lập"
              stackId="1"
              stroke="#94a3b8"
              fill="#94a3b8"
              fillOpacity={0.6}
            />
            <Area
              type="monotone"
              dataKey="negative"
              name="Tiêu cực"
              stackId="1"
              stroke="#ef4444"
              fill="#ef4444"
              fillOpacity={0.6}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/analytics/SentimentTrend.tsx
git commit -m "feat(analytics): add SentimentTrend chart component"
```

---

## Task 9: KeywordCloud Component

**Files:**
- Create: `frontend/components/analytics/KeywordCloud.tsx`

- [ ] **Step 1: Create the KeywordCloud component**

Create `frontend/components/analytics/KeywordCloud.tsx`:

```tsx
"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { KeywordEntry } from "@/lib/api";

interface Props {
  keywords: KeywordEntry[];
  title?: string;
}

export function KeywordCloud({ keywords, title = "Từ khóa nổi bật" }: Props) {
  if (keywords.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        </CardContent>
      </Card>
    );
  }

  // Take top 15, sorted descending by count
  const chartData = keywords.slice(0, 15).reverse();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 28)}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 60 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" tick={{ fontSize: 12 }} />
            <YAxis
              type="category"
              dataKey="word"
              tick={{ fontSize: 12 }}
              width={55}
            />
            <Tooltip />
            <Bar dataKey="count" name="Số lần" fill="#3b82f6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/analytics/KeywordCloud.tsx
git commit -m "feat(analytics): add KeywordCloud bar chart component"
```

---

## Task 10: SessionList Component

**Files:**
- Create: `frontend/components/analytics/SessionList.tsx`

- [ ] **Step 1: Create the SessionList component**

Create `frontend/components/analytics/SessionList.tsx`:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SessionListEntry } from "@/lib/api";

interface Props {
  sessions: SessionListEntry[];
}

const INTENT_LABELS: Record<string, string> = {
  product_inquiry: "Hỏi SP",
  greeting: "Chào hỏi",
  unknown: "Không rõ",
  skipped: "Bỏ qua",
  blacklist: "Từ cấm",
  none: "—",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)} phút`;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return `${h}h${m > 0 ? ` ${m}p` : ""}`;
}

export function SessionList({ sessions }: Props) {
  const router = useRouter();

  if (sessions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Danh sách buổi live</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Chưa có buổi live nào.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Danh sách buổi live</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="pb-2 pr-4 font-medium">Ngày/Giờ</th>
              <th className="pb-2 pr-4 font-medium">Thời lượng</th>
              <th className="pb-2 pr-4 font-medium text-right">Comments</th>
              <th className="pb-2 pr-4 font-medium text-right">Reply %</th>
              <th className="pb-2 pr-4 font-medium text-right">Gifts</th>
              <th className="pb-2 font-medium">Top Intent</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr
                key={s.id}
                className="border-b cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => router.push(`/analytics/sessions/${s.id}`)}
              >
                <td className="py-2 pr-4">{formatDate(s.started_at)}</td>
                <td className="py-2 pr-4">{formatDuration(s.duration_minutes)}</td>
                <td className="py-2 pr-4 text-right">{s.comment_count}</td>
                <td className="py-2 pr-4 text-right">{s.reply_rate}%</td>
                <td className="py-2 pr-4 text-right">
                  {s.gift_count > 0 ? `${s.gift_count} (${s.gift_diamonds}💎)` : "—"}
                </td>
                <td className="py-2">{INTENT_LABELS[s.top_intent] ?? s.top_intent}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/analytics/SessionList.tsx
git commit -m "feat(analytics): add SessionList table component with drilldown"
```

---

## Task 11: Update Overview Page

**Files:**
- Modify: `frontend/app/analytics/page.tsx`

- [ ] **Step 1: Add new sections to the overview page**

Replace the entire file `frontend/app/analytics/page.tsx` with:

```tsx
"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { StatsCards } from "@/components/analytics/StatsCards";
import { IntentBreakdown } from "@/components/analytics/IntentBreakdown";
import { UnansweredSummary } from "@/components/analytics/UnansweredSummary";
import { DateRangeFilter } from "@/components/analytics/DateRangeFilter";
import { GiftStatsSection } from "@/components/analytics/GiftStats";
import { SentimentTrend } from "@/components/analytics/SentimentTrend";
import { KeywordCloud } from "@/components/analytics/KeywordCloud";
import { SessionList } from "@/components/analytics/SessionList";
import { api, type AnalyticsData } from "@/lib/api";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  function load() {
    setError(false);
    setLoading(true);
    api.analytics
      .get({
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      })
      .then(setData)
      .catch(() => {
        setData(null);
        setError(true);
        toast.error("Failed to load analytics");
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Analytics</h2>
          <p className="text-sm text-muted-foreground">
            Live session statistics
            {startDate && endDate
              ? ` from ${startDate} to ${endDate}`
              : " (all time)"}
          </p>
        </div>
      </div>

      <DateRangeFilter
        startDate={startDate}
        endDate={endDate}
        onStartChange={setStartDate}
        onEndChange={setEndDate}
        onApply={load}
        loading={loading}
      />

      {error && (
        <div className="space-y-2">
          <p className="text-sm text-destructive">Failed to load data.</p>
          <button
            onClick={load}
            className="text-sm underline"
          >
            Retry
          </button>
        </div>
      )}

      {loading && !data && (
        <p className="text-sm text-muted-foreground">Loading...</p>
      )}

      {data && (
        <div className="space-y-6">
          <StatsCards data={data} />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <IntentBreakdown breakdown={data.intent_breakdown} />
            <UnansweredSummary count={data.unanswered_count} />
          </div>
          {data.gift_stats && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Gift & Revenue</h3>
              <GiftStatsSection stats={data.gift_stats} />
            </div>
          )}

          {/* Deep Analytics sections */}
          <SentimentTrend data={data.sentiment_trend} />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <KeywordCloud keywords={data.top_keywords_overall} />
            <div /> {/* Placeholder for visual balance */}
          </div>
          <SessionList sessions={data.session_list} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify build compiles**

Run (from `frontend/` directory): `npx tsc --noEmit`

Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/app/analytics/page.tsx
git commit -m "feat(analytics): add sentiment trend, keywords, session list to overview"
```

---

## Task 12: ActivityTimeline Component

**Files:**
- Create: `frontend/components/analytics/ActivityTimeline.tsx`

- [ ] **Step 1: Create the ActivityTimeline component**

Create `frontend/components/analytics/ActivityTimeline.tsx`:

```tsx
"use client";

import {
  ComposedChart,
  Area,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TimelineBucket } from "@/lib/api";

interface Props {
  data: TimelineBucket[];
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

export function ActivityTimeline({ data }: Props) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Timeline hoạt động</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        </CardContent>
      </Card>
    );
  }

  const chartData = data.map((b) => ({
    ...b,
    time: formatTime(b.bucket_start),
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Timeline hoạt động</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" tick={{ fontSize: 12 }} />
            <YAxis
              yAxisId="left"
              tick={{ fontSize: 12 }}
              label={{ value: "Comments", angle: -90, position: "insideLeft", fontSize: 11 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 12 }}
              label={{ value: "Diamonds", angle: 90, position: "insideRight", fontSize: 11 }}
            />
            <Tooltip />
            <Legend />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="comment_count"
              name="Comments"
              stroke="#3b82f6"
              fill="#3b82f6"
              fillOpacity={0.3}
            />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="reply_count"
              name="Replies"
              stroke="#22c55e"
              fill="#22c55e"
              fillOpacity={0.2}
            />
            <Bar
              yAxisId="right"
              dataKey="gift_diamonds"
              name="Diamonds"
              fill="#f59e0b"
              opacity={0.8}
              radius={[2, 2, 0, 0]}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/analytics/ActivityTimeline.tsx
git commit -m "feat(analytics): add ActivityTimeline composed chart component"
```

---

## Task 13: SentimentBreakdown Component

**Files:**
- Create: `frontend/components/analytics/SentimentBreakdown.tsx`

- [ ] **Step 1: Create the SentimentBreakdown component**

Create `frontend/components/analytics/SentimentBreakdown.tsx`:

```tsx
"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  data: Record<string, number>;
}

const COLORS: Record<string, string> = {
  positive: "#22c55e",
  neutral: "#94a3b8",
  negative: "#ef4444",
};

const LABELS: Record<string, string> = {
  positive: "Tích cực",
  neutral: "Trung lập",
  negative: "Tiêu cực",
};

export function SentimentBreakdown({ data }: Props) {
  const entries = Object.entries(data).filter(([, v]) => v > 0);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);

  if (total === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Phân bố cảm xúc</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        </CardContent>
      </Card>
    );
  }

  const chartData = entries.map(([name, value]) => ({
    name: LABELS[name] ?? name,
    value,
    color: COLORS[name] ?? "#6b7280",
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Phân bố cảm xúc</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={90}
              dataKey="value"
              nameKey="name"
              label={({ name, percent }) =>
                `${name} ${(percent * 100).toFixed(0)}%`
              }
              labelLine={false}
            >
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
        <p className="text-center text-sm text-muted-foreground mt-1">
          Tổng: {total} comments
        </p>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/analytics/SentimentBreakdown.tsx
git commit -m "feat(analytics): add SentimentBreakdown pie chart component"
```

---

## Task 14: EngagementMetrics Component

**Files:**
- Create: `frontend/components/analytics/EngagementMetrics.tsx`

- [ ] **Step 1: Create the EngagementMetrics component**

Create `frontend/components/analytics/EngagementMetrics.tsx`:

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EngagementMetrics as EngagementMetricsType } from "@/lib/api";

interface Props {
  metrics: EngagementMetricsType;
}

function formatPeakMinute(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

export function EngagementMetrics({ metrics }: Props) {
  const cards = [
    {
      label: "Tỷ lệ hỏi sản phẩm",
      value: `${metrics.product_inquiry_rate}%`,
      description: "Proxy conversion rate",
    },
    {
      label: "Người bình luận",
      value: metrics.unique_commenters,
      description: "Unique commenters",
    },
    {
      label: "Comments/phút",
      value: metrics.comments_per_minute_avg,
      description: "Trung bình",
    },
    {
      label: "Phút cao điểm",
      value: metrics.peak_minute
        ? `${formatPeakMinute(metrics.peak_minute)} (${metrics.peak_comments})`
        : "—",
      description: "Thời điểm + số comments",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {cards.map((c) => (
        <Card key={c.label}>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {c.label}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{c.value}</p>
            <p className="text-xs text-muted-foreground">{c.description}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/analytics/EngagementMetrics.tsx
git commit -m "feat(analytics): add EngagementMetrics KPI cards component"
```

---

## Task 15: Session Detail Page

**Files:**
- Create: `frontend/app/analytics/sessions/[id]/page.tsx`

- [ ] **Step 1: Create the session detail page**

Create directories and file `frontend/app/analytics/sessions/[id]/page.tsx`:

```bash
mkdir -p frontend/app/analytics/sessions/\[id\]
```

Create `frontend/app/analytics/sessions/[id]/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { api, type SessionAnalyticsData } from "@/lib/api";
import { ActivityTimeline } from "@/components/analytics/ActivityTimeline";
import { KeywordCloud } from "@/components/analytics/KeywordCloud";
import { SentimentBreakdown } from "@/components/analytics/SentimentBreakdown";
import { IntentBreakdown } from "@/components/analytics/IntentBreakdown";
import { EngagementMetrics } from "@/components/analytics/EngagementMetrics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)} phút`;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return `${h} giờ${m > 0 ? ` ${m} phút` : ""}`;
}

export default function SessionDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<SessionAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!params.id) return;
    setLoading(true);
    setError(false);
    api.analytics
      .session(params.id)
      .then(setData)
      .catch((err) => {
        setError(true);
        toast.error(err.message || "Không thể tải dữ liệu session");
      })
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return <p className="text-sm text-muted-foreground p-6">Đang tải...</p>;
  }

  if (error || !data) {
    return (
      <div className="p-6 space-y-2">
        <p className="text-sm text-destructive">Không thể tải dữ liệu.</p>
        <button onClick={() => router.back()} className="text-sm underline">
          Quay lại
        </button>
      </div>
    );
  }

  const { session_info, summary, timeline, top_keywords, intent_breakdown, sentiment_breakdown, engagement_metrics } = data;

  const summaryCards = [
    { label: "Comments", value: summary.total_comments },
    { label: "Replies", value: summary.total_replies },
    { label: "Tỷ lệ reply", value: `${summary.reply_rate}%` },
    { label: "Gifts", value: summary.total_gifts },
    { label: "Diamonds", value: summary.total_diamonds },
    { label: "USD", value: `$${summary.estimated_usd}` },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.push("/analytics")}
          className="text-sm text-muted-foreground hover:text-foreground underline"
        >
          &larr; Analytics
        </button>
        <div>
          <h2 className="text-2xl font-bold">
            Session {formatDateTime(session_info.started_at)}
          </h2>
          <p className="text-sm text-muted-foreground">
            {formatDuration(session_info.duration_minutes)}
            {session_info.ended_at
              ? ` — kết thúc ${formatDateTime(session_info.ended_at)}`
              : " — đang diễn ra"}
          </p>
        </div>
      </div>

      {/* Summary KPI cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {summaryCards.map((c) => (
          <Card key={c.label}>
            <CardHeader className="pb-1">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {c.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{c.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Activity Timeline */}
      <ActivityTimeline data={timeline} />

      {/* Two-column: Keywords + Breakdowns */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <KeywordCloud keywords={top_keywords} title="Từ khóa trong session" />
        <div className="space-y-4">
          <IntentBreakdown breakdown={intent_breakdown} />
          <SentimentBreakdown data={sentiment_breakdown} />
        </div>
      </div>

      {/* Engagement Metrics */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Chỉ số tương tác</h3>
        <EngagementMetrics metrics={engagement_metrics} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run (from `frontend/` directory): `npx tsc --noEmit`

Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/app/analytics/sessions/\[id\]/page.tsx
git commit -m "feat(analytics): add session detail page with timeline, keywords, engagement"
```

---

## Task 16: Final Verification

- [ ] **Step 1: Run all backend tests**

Run: `python3 -m pytest backend/tests/ -v`

Expected: All tests PASS

- [ ] **Step 2: Run frontend type check**

Run (from `frontend/` directory): `npx tsc --noEmit`

Expected: No errors

- [ ] **Step 3: Run frontend build**

Run (from `frontend/` directory): `npm run build`

Expected: Build succeeds

- [ ] **Step 4: Run frontend lint**

Run (from `frontend/` directory): `npm run lint`

Expected: No errors (or only pre-existing warnings)

- [ ] **Step 5: Final commit (if any remaining changes)**

```bash
git status
# If any uncommitted changes:
git add -A
git commit -m "chore: final verification fixes for deep analytics"
```
