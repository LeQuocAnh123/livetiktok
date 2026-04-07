import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.session import LiveSession


class MessageLog(Base):
    __tablename__ = "message_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("live_sessions.id"), nullable=False)
    user_unique_id: Mapped[str] = mapped_column(String, nullable=False)
    comment: Mapped[str] = mapped_column(String, nullable=False)
    reply: Mapped[str | None] = mapped_column(String, nullable=True)
    intent: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    sentiment: Mapped[str] = mapped_column(String, nullable=False, default="neutral")
    chunks_used: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["LiveSession"] = relationship(back_populates="messages")
