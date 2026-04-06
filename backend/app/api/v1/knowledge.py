"""Knowledge Base CRUD API."""
import csv
import io
import logging
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai.factory import get_embed_provider
from app.core.rag import retriever
from app.database import get_db, get_session_factory
from app.models.knowledge import KnowledgeChunk, KnowledgeCategory
from app.models.seller import Seller
from app.schemas.knowledge import (
    CsvPreviewResponse,
    KnowledgeChunkCreate,
    KnowledgeChunkResponse,
    KnowledgeChunkUpdate,
    KnowledgeListResponse,
    PreviewRow,
    UploadResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

MAX_UPLOAD_ROWS = 500


async def embed_and_store(chunk_id: str, seller_id: str) -> None:
    """Background task: embed chunk content and upsert into ChromaDB."""
    async with get_session_factory()() as db:
        chunk = await db.get(KnowledgeChunk, chunk_id)
        if chunk is None or not chunk.needs_reembed:
            return
        try:
            embed_provider = get_embed_provider()
            embedding = await embed_provider.embed(chunk.content)
            await retriever.add_chunk(
                seller_id=seller_id,
                chunk_id=chunk.id,
                content=chunk.content,
                embedding=embedding,
                metadata={"category": chunk.category.value, **chunk.metadata_},
            )
            chunk.needs_reembed = False
            await db.commit()
            logger.info("Embedded chunk %s", chunk_id)
        except Exception:
            logger.exception("Failed to embed chunk %s", chunk_id)


async def _require_seller(seller_id: str, db: AsyncSession) -> None:
    """Raise 404 if seller does not exist."""
    seller = await db.get(Seller, seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")


@router.post("/", response_model=KnowledgeChunkResponse, status_code=201)
async def create_chunk(
    body: KnowledgeChunkCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    await _require_seller(body.seller_id, db)
    chunk = KnowledgeChunk(
        seller_id=body.seller_id,
        content=body.content,
        category=body.category,
        metadata_=body.metadata,
        needs_reembed=True,
    )
    db.add(chunk)
    await db.commit()
    await db.refresh(chunk)
    background_tasks.add_task(embed_and_store, chunk.id, body.seller_id)
    return KnowledgeChunkResponse.from_orm_model(chunk)


@router.get("/", response_model=KnowledgeListResponse)
async def list_chunks(
    seller_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    count_result = await db.execute(
        select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.seller_id == seller_id)
    )
    total = count_result.scalar() or 0

    items_result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.seller_id == seller_id)
        .offset(offset)
        .limit(limit)
    )
    items = items_result.scalars().all()

    return KnowledgeListResponse(
        items=[KnowledgeChunkResponse.from_orm_model(c) for c in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.put("/{chunk_id}", response_model=KnowledgeChunkResponse)
async def update_chunk(
    chunk_id: str,
    body: KnowledgeChunkUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    chunk = await db.get(KnowledgeChunk, chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")

    if body.content is not None:
        chunk.content = body.content
        chunk.needs_reembed = True
    if body.category is not None:
        chunk.category = body.category
        chunk.needs_reembed = True
    if body.metadata is not None:
        chunk.metadata_ = body.metadata

    await db.commit()
    await db.refresh(chunk)

    if chunk.needs_reembed:
        background_tasks.add_task(embed_and_store, chunk.id, chunk.seller_id)

    return KnowledgeChunkResponse.from_orm_model(chunk)


@router.delete("/{chunk_id}", status_code=204)
async def delete_chunk_endpoint(
    chunk_id: str,
    db: AsyncSession = Depends(get_db),
):
    chunk = await db.get(KnowledgeChunk, chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")

    await retriever.delete_chunk(chunk.seller_id, chunk_id)
    await db.delete(chunk)
    await db.commit()


def _parse_csv_bytes(content_bytes: bytes) -> list[dict]:
    text = content_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _validate_rows(rows: list[dict]) -> tuple[list[PreviewRow], list[str]]:
    """Return (preview_rows, file_level_warnings)."""
    valid_categories = {c.value for c in KnowledgeCategory}
    preview_rows: list[PreviewRow] = []
    for i, row in enumerate(rows, start=1):
        content = row.get("content", "").strip()
        raw_cat = row.get("category", "faq").strip().lower()
        warning = None
        is_valid = True
        if not content:
            warning = "Cột content trống"
            is_valid = False
        elif raw_cat not in valid_categories:
            warning = f"Category '{raw_cat}' không hợp lệ → sẽ dùng 'faq'"
        preview_rows.append(PreviewRow(
            row=i, content=content, category=raw_cat, is_valid=is_valid, warning=warning
        ))

    warnings: list[str] = []
    empty = sum(1 for r in rows if not r.get("content", "").strip())
    bad_cat = sum(1 for r in rows if r.get("category", "faq").strip().lower() not in valid_categories)
    if empty:
        warnings.append(f"{empty} dòng có content trống sẽ bị bỏ qua")
    if bad_cat:
        warnings.append(f"{bad_cat} dòng có category không hợp lệ sẽ được đặt thành 'faq'")
    return preview_rows, warnings


@router.post("/preview", response_model=CsvPreviewResponse)
async def preview_knowledge(file: UploadFile):
    """Parse CSV and return preview without saving anything."""
    filename = file.filename or ""
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content_bytes = await file.read()
    rows = _parse_csv_bytes(content_bytes)

    if not rows or "content" not in (rows[0].keys() if rows else []):
        raise HTTPException(status_code=400, detail="CSV must have a 'content' column")

    if len(rows) > MAX_UPLOAD_ROWS:
        raise HTTPException(status_code=400, detail=f"File vượt quá {MAX_UPLOAD_ROWS} dòng (có {len(rows)})")

    valid_rows = sum(1 for r in rows if r.get("content", "").strip())
    preview_rows, warnings = _validate_rows(rows)

    return CsvPreviewResponse(
        total_rows=len(rows),
        valid_rows=valid_rows,
        preview=preview_rows,
        warnings=warnings,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_knowledge(
    seller_id: str,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Bulk import from CSV. Columns: content (required), category (optional), + any metadata cols."""
    filename = file.filename or ""
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content_bytes = await file.read()
    rows = _parse_csv_bytes(content_bytes)

    if len(rows) > MAX_UPLOAD_ROWS:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum {MAX_UPLOAD_ROWS} rows (got {len(rows)})",
        )

    if not rows or "content" not in rows[0].keys():
        raise HTTPException(status_code=400, detail="CSV must have a 'content' column")

    await _require_seller(seller_id, db)

    created = 0
    skipped = 0
    errors: list[str] = []

    chunks = []
    for i, row in enumerate(rows, start=1):
        raw_content = row.get("content", "").strip()
        if not raw_content:
            skipped += 1
            continue

        raw_category = row.get("category", "faq").strip().lower()
        try:
            category = KnowledgeCategory(raw_category)
        except ValueError:
            category = KnowledgeCategory.FAQ
            errors.append(f"Dòng {i}: category '{raw_category}' không hợp lệ, dùng 'faq'")

        metadata: dict[str, Any] = {
            k: v for k, v in row.items() if k not in ("content", "category") and v
        }

        chunk = KnowledgeChunk(
            seller_id=seller_id,
            content=raw_content,
            category=category,
            metadata_=metadata,
            needs_reembed=True,
        )
        db.add(chunk)
        chunks.append(chunk)
        created += 1

    await db.commit()
    for chunk in chunks:
        await db.refresh(chunk)
        background_tasks.add_task(embed_and_store, chunk.id, seller_id)

    return UploadResponse(created=created, skipped=skipped, errors=errors)
