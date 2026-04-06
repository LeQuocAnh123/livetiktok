"""Pydantic schemas for Knowledge Base API."""
from typing import Any
from pydantic import BaseModel

from app.models.knowledge import KnowledgeCategory


class KnowledgeChunkCreate(BaseModel):
    seller_id: str
    content: str
    category: KnowledgeCategory = KnowledgeCategory.FAQ
    metadata: dict[str, Any] = {}


class KnowledgeChunkUpdate(BaseModel):
    content: str | None = None
    category: KnowledgeCategory | None = None
    metadata: dict[str, Any] | None = None


class KnowledgeChunkResponse(BaseModel):
    id: str
    seller_id: str
    content: str
    category: KnowledgeCategory
    metadata: dict[str, Any] = {}
    needs_reembed: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, obj) -> "KnowledgeChunkResponse":
        return cls(
            id=obj.id,
            seller_id=obj.seller_id,
            content=obj.content,
            category=obj.category,
            metadata=obj.metadata_,
            needs_reembed=obj.needs_reembed,
        )


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeChunkResponse]
    total: int
    page: int
    limit: int
