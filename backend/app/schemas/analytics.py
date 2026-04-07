from pydantic import BaseModel, Field

from app.schemas.gift import GiftStats


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
