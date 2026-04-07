"""Pydantic schemas for gift tracking."""

from datetime import datetime

from pydantic import BaseModel


class GiftLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    session_id: str
    user_unique_id: str
    gift_name: str
    diamond_count: int
    repeat_count: int
    total_diamonds: int
    estimated_usd: float
    thank_reply: str | None
    created_at: datetime


class TopGifter(BaseModel):
    user: str
    total_diamonds: int
    gift_count: int


class GiftBreakdown(BaseModel):
    gift_name: str
    count: int
    total_diamonds: int


class GiftStats(BaseModel):
    total_gifts: int
    total_diamonds: int
    estimated_usd: float
    top_gifters: list[TopGifter]
    gift_breakdown: list[GiftBreakdown]
