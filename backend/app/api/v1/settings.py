"""Settings API — get/update bot settings, test-reply preview."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_seller
from app.core.ai.base import LLMResult
from app.core.ai.factory import get_embed_provider, get_reply_provider
from app.core.rag import retriever
from app.core.rag.overrides import get_recent_overrides
from app.core.rag.pipeline import SYSTEM_PROMPT_TEMPLATE, _format_override_examples
from app.database import get_db
from app.models.seller import Seller
from app.schemas.settings import (
    BotSettingsResponse,
    BotSettingsUpdate,
    TestReplyRequest,
    TestReplyResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("/", response_model=BotSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
):
    # Refresh from DB to get latest settings
    await db.refresh(current_seller)
    return BotSettingsResponse(**current_seller.bot_settings)


@router.put("/", response_model=BotSettingsResponse)
async def update_settings(
    body: BotSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
):
    # Merge: only update fields that were explicitly provided
    updated = dict(current_seller.bot_settings)
    patch = body.model_dump(exclude_none=True)
    updated.update(patch)
    current_seller.bot_settings = updated

    await db.commit()
    await db.refresh(current_seller)
    return BotSettingsResponse(**current_seller.bot_settings)


@router.post("/test-reply", response_model=TestReplyResponse)
async def test_reply(
    body: TestReplyRequest,
    db: AsyncSession = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller),
):
    """Run the full RAG pipeline for a comment and return the preview reply.
    Does NOT send anything to TikTok."""
    settings = current_seller.bot_settings
    seller_id = current_seller.id

    # Blacklist check
    blacklist = settings.get("blacklist_keywords", [])
    comment_lower = body.comment.lower()
    if any(kw.lower() in comment_lower for kw in blacklist):
        return TestReplyResponse(
            reply="[Bị chặn] Comment chứa từ khoá bị cấm.",
            intent="blacklist",
            sentiment="neutral",
            chunks_used=[],
        )

    embed_provider = get_embed_provider()
    embedding = await embed_provider.embed(body.comment)

    chunks = await retriever.query(seller_id, embedding, n_results=3)
    context = "\n\n".join(c["content"] for c in chunks)

    # Fetch override examples and build prompt
    overrides = await get_recent_overrides(seller_id, db, limit=5)
    override_block = _format_override_examples(overrides)
    system = SYSTEM_PROMPT_TEMPLATE.format(
        tone=settings.get("tone", "friendly"),
        override_examples=override_block,
    )

    reply_provider = get_reply_provider()
    llm_result: LLMResult = await reply_provider.generate_reply(
        system=system, context=context, user_msg=body.comment
    )

    return TestReplyResponse(
        reply=llm_result.reply,
        intent=llm_result.intent,
        sentiment=llm_result.sentiment,
        chunks_used=[c["id"] for c in chunks],
    )
