from pydantic import BaseModel


class AnalyticsResponse(BaseModel):
    total_sessions: int
    total_comments: int
    total_replies: int
    reply_rate: float  # 0-100
    intent_breakdown: dict[str, int]  # intent -> count
    unanswered_count: int
