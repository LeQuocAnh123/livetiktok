"""Settings API — get/update bot settings, test-reply preview."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai.factory import get_embed_provider, get_reply_provider
from app.core.rag import retriever
from app.core.rag.filter import detect_intent
from app.core.rag.pipeline import SYSTEM_PROMPT_TEMPLATE
from app.database import get_db
from app.models.seller import Seller
from app.schemas.settings import BotSettingsResponse, BotSettingsUpdate, TestReplyRequest, TestReplyResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


async def _get_seller(seller_id: str, db: AsyncSession) -> Seller:
    seller = await db.get(Seller, seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")
    return seller


@router.get("/", response_model=BotSettingsResponse)
async def get_settings(seller_id: str, db: AsyncSession = Depends(get_db)):
    seller = await _get_seller(seller_id, db)
    return BotSettingsResponse(**seller.bot_settings)


@router.put("/", response_model=BotSettingsResponse)
async def update_settings(
    seller_id: str,
    body: BotSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    seller = await _get_seller(seller_id, db)

    # Merge: only update fields that were explicitly provided
    updated = dict(seller.bot_settings)
    patch = body.model_dump(exclude_none=True)
    updated.update(patch)
    seller.bot_settings = updated

    await db.commit()
    await db.refresh(seller)
    return BotSettingsResponse(**seller.bot_settings)


@router.post("/test-reply", response_model=TestReplyResponse)
async def test_reply(body: TestReplyRequest, db: AsyncSession = Depends(get_db)):
    """Run the full RAG pipeline for a comment and return the preview reply.
    Does NOT send anything to TikTok."""
    seller = await _get_seller(body.seller_id, db)
    settings = seller.bot_settings

    intent = detect_intent(body.comment)

    embed_provider = get_embed_provider()
    embedding = await embed_provider.embed(body.comment)

    chunks = await retriever.query(body.seller_id, embedding, n_results=3)
    context = "\n\n".join(c["content"] for c in chunks)
    system = SYSTEM_PROMPT_TEMPLATE.format(tone=settings.get("tone", "friendly"))

    reply_provider = get_reply_provider()
    reply = await reply_provider.generate_reply(system=system, context=context, user_msg=body.comment)

    return TestReplyResponse(
        reply=reply,
        intent=intent,
        chunks_used=[c["id"] for c in chunks],
    )
