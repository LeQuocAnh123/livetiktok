"""RAG Pipeline — orchestrates filter → embed → retrieve → prompt → reply."""
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.core.rag.filter import CommentFilter, detect_intent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """\
Bạn là AI assistant hỗ trợ bán hàng trên TikTok Live. Nhiệm vụ của bạn là trả lời \
câu hỏi từ người xem livestream dựa trên thông tin sản phẩm được cung cấp.

Quy tắc:
- Luôn trả lời bằng tiếng Việt
- Ngắn gọn, thân thiện (tối đa 2-3 câu)
- Chỉ dùng thông tin trong Context, không bịa đặt
- Nếu không có thông tin phù hợp, nói "Để em hỏi lại và phản hồi sau nhé ạ!"
- Tone: {tone}"""


@dataclass
class RAGResult:
    intent: str
    reply: str | None
    chunks_used: list[str]
    skipped: bool
    skip_reason: str | None = None


@dataclass
class RAGPipeline:
    """
    Orchestrates the full RAG comment-reply flow.

    Inject dependencies via constructor to keep this testable without
    real API calls or a running ChromaDB instance.
    """

    seller_id: str
    seller_settings: dict[str, Any]
    embed_fn: Callable[[str], Awaitable[list[float]]]
    retrieve_fn: Callable[[str, list[float], int], Awaitable[list[dict]]]
    generate_reply_fn: Callable[..., Awaitable[str]]
    _filter: CommentFilter = field(init=False)

    def __post_init__(self) -> None:
        self._filter = CommentFilter(self.seller_settings)

    async def process(self, user_id: str, comment: str) -> RAGResult:
        """Process one comment through the full pipeline."""
        # 1. Filter
        filter_result = self._filter.check(user_id, comment)
        if filter_result.skip:
            logger.info("Comment skipped (reason=%s): %s", filter_result.reason, comment[:40])
            return RAGResult(
                intent="skipped",
                reply=None,
                chunks_used=[],
                skipped=True,
                skip_reason=filter_result.reason,
            )

        # 2. Detect intent
        intent = detect_intent(comment)

        # 3. Embed comment
        embedding = await self.embed_fn(comment)

        # 4. Retrieve top-3 chunks
        chunks = await self.retrieve_fn(self.seller_id, embedding, 3)

        # 5. Build context and system prompt
        context = "\n\n".join(c["content"] for c in chunks)
        system = SYSTEM_PROMPT_TEMPLATE.format(
            tone=self.seller_settings.get("tone", "friendly")
        )

        # 6. Generate reply
        reply = await self.generate_reply_fn(
            system=system,
            context=context,
            user_msg=comment,
        )

        # 7. Record cooldown
        self._filter.update_cooldown(user_id)

        logger.info("Reply for %s (intent=%s): %s", user_id, intent, reply[:60])
        return RAGResult(
            intent=intent,
            reply=reply,
            chunks_used=[c["id"] for c in chunks],
            skipped=False,
        )
