import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.message import MessageLog
    from app.models.seller import Seller


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"
    PAUSED = "paused"


class LiveSession(Base):
    __tablename__ = "live_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id: Mapped[str] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    tiktok_room_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[SessionStatus] = mapped_column(String, nullable=False, default=SessionStatus.ACTIVE)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    seller: Mapped["Seller"] = relationship(back_populates="sessions")
    messages: Mapped[list["MessageLog"]] = relationship(back_populates="session")
