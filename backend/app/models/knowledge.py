import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.seller import Seller


class KnowledgeCategory(str, Enum):
    PRODUCT = "product"
    POLICY = "policy"
    FAQ = "faq"


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id: Mapped[str] = mapped_column(ForeignKey("sellers.id"), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[KnowledgeCategory] = mapped_column(String, nullable=False, default=KnowledgeCategory.FAQ)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    needs_reembed: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    seller: Mapped["Seller"] = relationship(back_populates="knowledge_chunks")
