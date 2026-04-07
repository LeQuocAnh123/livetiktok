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
