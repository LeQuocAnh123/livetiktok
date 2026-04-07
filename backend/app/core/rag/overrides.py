"""Fetch recent seller manual override examples for few-shot prompt injection."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import MessageLog
from app.models.session import LiveSession

logger = logging.getLogger(__name__)


async def get_recent_overrides(
    seller_id: str,
    db: AsyncSession,
    limit: int = 5,
) -> list[tuple[str, str]]:
    """Return (comment, reply) pairs from recent manual overrides for a seller.

    Queries MessageLog entries where intent='manual' and reply is not null,
    joined through LiveSession to filter by seller_id.
    Results are ordered by created_at DESC and limited.
    """
    result = await db.execute(
        select(MessageLog.comment, MessageLog.reply)
        .join(LiveSession, MessageLog.session_id == LiveSession.id)
        .where(
            LiveSession.seller_id == seller_id,
            MessageLog.intent == "manual",
            MessageLog.reply.is_not(None),
        )
        .order_by(MessageLog.created_at.desc())
        .limit(limit)
    )
    rows = result.all()
    return [(row[0], row[1]) for row in rows]
