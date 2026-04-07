import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.session import LiveSession


class GiftLog(Base):
    __tablename__ = "gift_logs"
    __table_args__ = (
        Index(
            "ix_gift_dedup",
            "session_id",
            "user_unique_id",
            "gift_name",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("live_sessions.id"), nullable=False)
    user_unique_id: Mapped[str] = mapped_column(String, nullable=False)
    gift_name: Mapped[str] = mapped_column(String, nullable=False)
    diamond_count: Mapped[int] = mapped_column(Integer, nullable=False)
    repeat_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_diamonds: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_usd: Mapped[float] = mapped_column(Float, nullable=False)
    thank_reply: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["LiveSession"] = relationship(back_populates="gifts")
