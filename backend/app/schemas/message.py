from datetime import datetime
from typing import Any
from pydantic import BaseModel


class MessageLogSchema(BaseModel):
    id: str
    session_id: str
    user_unique_id: str
    comment: str
    reply: str | None = None
    intent: str
    chunks_used: list[Any] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class WSMessage(BaseModel):
    """WebSocket message envelope."""
    type: str  # comment | reply | status | error
    payload: dict[str, Any]
