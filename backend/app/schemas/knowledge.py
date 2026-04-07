"""Pydantic schemas for Knowledge Base API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from app.models.knowledge import KnowledgeCategory

if TYPE_CHECKING:
    from app.models.knowledge import KnowledgeChunk


class KnowledgeChunkCreate(BaseModel):
    content: str
    category: KnowledgeCategory = KnowledgeCategory.FAQ
    metadata: dict[str, Any] = {}
    # seller_id removed - comes from JWT


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
    def from_orm_model(cls, obj: "KnowledgeChunk") -> "KnowledgeChunkResponse":
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


class UploadResponse(BaseModel):
    created: int
    skipped: int
    errors: list[str]


class PreviewRow(BaseModel):
    row: int
    content: str
    category: str
    is_valid: bool
    warning: str | None


class CsvPreviewResponse(BaseModel):
    total_rows: int
    valid_rows: int
    preview: list[PreviewRow]  # all rows
    warnings: list[str]  # file-level warnings
