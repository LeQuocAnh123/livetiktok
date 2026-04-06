from datetime import datetime
from pydantic import BaseModel
from app.models.session import SessionStatus


class SessionStartRequest(BaseModel):
    seller_id: str
    tiktok_unique_id: str


class SessionResponse(BaseModel):
    id: str
    seller_id: str
    tiktok_room_id: int | None = None
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None = None

    model_config = {"from_attributes": True}


class SessionStatusResponse(BaseModel):
    connected: bool
    session: SessionResponse | None = None
