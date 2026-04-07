"""RAG Pipeline — orchestrates filter -> embed -> retrieve -> override fetch -> prompt -> reply."""

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.core.ai.base import LLMResult
from app.core.rag.filter import CommentFilter

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """\
Bạn là AI assistant hỗ trợ bán hàng trên TikTok Live. Nhiệm vụ của bạn là trả lời \
câu hỏi từ người xem livestream dựa trên thông tin sản phẩm được cung cấp.

Quy tắc:
- Luôn trả lời bằng tiếng Việt
- Ngắn gọn, thân thiện (tối đa 2-3 câu)
- Chỉ dùng thông tin trong Context, không bịa đặt
- Nếu câu hỏi không liên quan đến sản phẩm/dịch vụ của shop, trả lời ngắn gọn: \
"Dạ bên em chuyên về [lĩnh vực shop], bên em không hỗ trợ vấn đề này ạ!" rồi kết thúc, không cần hỏi SĐT
- Nếu không có thông tin phù hợp trong Context, nói "Để em hỏi lại và phản hồi sau nhé ạ!"
- Tone: {tone}

{override_examples}\
Trả lời dưới dạng JSON với đúng 3 field:
- "intent": phân loại ý định của comment ("product_inquiry" | "greeting" | "complaint" | "spam" | "other")
- "sentiment": cảm xúc của comment ("positive" | "neutral" | "negative")
- "reply": nội dung trả lời"""

GIFT_PROMPT_TEMPLATE = """\
Bạn là AI assistant hỗ trợ bán hàng trên TikTok Live. Một viewer vừa tặng gift cho bạn.

Quy tắc:
- Luôn trả lời bằng tiếng Việt
- Ngắn gọn, chân thành (1-2 câu)
- Cảm ơn viewer đã tặng gift, có thể nhắc tên gift
- Tone: {tone}

Trả lời dưới dạng JSON với đúng 3 field:
- "intent": luôn là "gift_thank"
- "sentiment": cảm xúc tổng thể ("positive" | "neutral" | "negative")
- "reply": nội dung cảm ơn"""


def _format_override_examples(overrides: list[tuple[str, str]]) -> str:
    """Format override examples for system prompt injection."""
    if not overrides:
        return ""
    lines = [
        "Dưới đây là một số ví dụ cách shop đã trả lời trước đó.",
        "Hãy học theo phong cách này:\n",
    ]
    for comment, reply in overrides:
        lines.append(f'Viewer: "{comment}"')
        lines.append(f'Shop: "{reply}"\n')
    return "\n".join(lines) + "\n"


@dataclass
class RAGResult:
    intent: str
    sentiment: str
    reply: str | None
    chunks_used: list[str]
    skipped: bool
    skip_reason: str | None = None


@dataclass
class GiftReplyResult:
    """Result from gift thank-you generation."""

    reply: str
    sentiment: str


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
    generate_reply_fn: Callable[..., Awaitable[LLMResult]]
    fetch_overrides_fn: Callable[[str], Awaitable[list[tuple[str, str]]]]
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
                sentiment="neutral",
                reply=None,
                chunks_used=[],
                skipped=True,
                skip_reason=filter_result.reason,
            )

        # 2. Embed comment
        embedding = await self.embed_fn(comment)

        # 3. Retrieve top-3 chunks
        chunks = await self.retrieve_fn(self.seller_id, embedding, 3)

        # 4. Fetch recent seller override examples
        overrides = await self.fetch_overrides_fn(self.seller_id)

        # 5. Build context and system prompt
        context = "\n\n".join(c["content"] for c in chunks)
        override_block = _format_override_examples(overrides)
        system = SYSTEM_PROMPT_TEMPLATE.format(
            tone=self.seller_settings.get("tone", "friendly"),
            override_examples=override_block,
        )

        # 6. Generate structured reply (intent + sentiment + reply)
        llm_result: LLMResult = await self.generate_reply_fn(
            system=system,
            context=context,
            user_msg=comment,
        )

        # 7. Record cooldown
        self._filter.update_cooldown(user_id)

        logger.info(
            "Reply for %s (intent=%s, sentiment=%s): %s",
            user_id,
            llm_result.intent,
            llm_result.sentiment,
            llm_result.reply[:60],
        )
        return RAGResult(
            intent=llm_result.intent,
            sentiment=llm_result.sentiment,
            reply=llm_result.reply,
            chunks_used=[c["id"] for c in chunks],
            skipped=False,
        )

    async def process_gift(self, user_id: str, gift_context: str) -> GiftReplyResult:
        """Generate a thank-you reply for a gift event.

        Skips embedding, retrieval, and cooldown — gifts always get a response.
        """
        system = GIFT_PROMPT_TEMPLATE.format(
            tone=self.seller_settings.get("tone", "friendly"),
        )

        llm_result: LLMResult = await self.generate_reply_fn(
            system=system,
            context="",
            user_msg=gift_context,
        )

        logger.info(
            "Gift reply for %s (sentiment=%s): %s",
            user_id,
            llm_result.sentiment,
            llm_result.reply[:60],
        )
        return GiftReplyResult(
            reply=llm_result.reply,
            sentiment=llm_result.sentiment,
        )
