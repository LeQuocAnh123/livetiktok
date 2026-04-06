import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.knowledge import KnowledgeChunk
    from app.models.session import LiveSession


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    tiktok_unique_id: Mapped[str] = mapped_column(String, nullable=False)
    # Stored encrypted via Fernet — NEVER store plaintext
    tiktok_session_id_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    tiktok_target_idc_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    bot_settings: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {
            "tone": "friendly",
            "blacklist_keywords": [],
            "reply_delay_min": 5,
            "reply_delay_max": 15,
            "user_cooldown_seconds": 60,
            "max_replies_per_session": 500,
            "auto_reply_enabled": True,
        },
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sessions: Mapped[list["LiveSession"]] = relationship(back_populates="seller")
    knowledge_chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="seller")
