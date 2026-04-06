"""Pydantic schemas for Settings API."""
from pydantic import BaseModel


class BotSettingsUpdate(BaseModel):
    """All fields optional — PUT merges into existing settings."""
    tone: str | None = None
    blacklist_keywords: list[str] | None = None
    reply_delay_min: int | None = None
    reply_delay_max: int | None = None
    user_cooldown_seconds: int | None = None
    max_replies_per_session: int | None = None
    auto_reply_enabled: bool | None = None


class BotSettingsResponse(BaseModel):
    tone: str
    blacklist_keywords: list[str]
    reply_delay_min: int
    reply_delay_max: int
    user_cooldown_seconds: int
    max_replies_per_session: int
    auto_reply_enabled: bool


class TestReplyRequest(BaseModel):
    seller_id: str
    comment: str


class TestReplyResponse(BaseModel):
    reply: str
    intent: str
    chunks_used: list[str]
