"""Comment filter: blacklist keywords, intent detection, per-user cooldown."""
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Vietnamese e-commerce intent keywords
_INTENT_KEYWORDS: dict[str, list[str]] = {
    "product_inquiry": [
        "giá", "bao nhiêu", "mua", "đặt hàng", "order", "ship", "giao hàng",
        "giao", "size", "màu", "chất liệu", "còn hàng", "hết hàng", "mẫu",
        "sản phẩm", "hàng", "thanh toán", "cod", "chuyển khoản", "freeship",
        "discount", "giảm giá", "khuyến mãi", "tặng", "bộ", "set",
    ],
    "greeting": [
        "hello", "hi", "chào", "alo", "hey", "xin chào", "shop ơi",
    ],
}


def detect_intent(text: str) -> str:
    """Return detected intent: 'product_inquiry' | 'greeting' | 'unknown'."""
    text_lower = text.lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return intent
    return "unknown"


@dataclass
class FilterResult:
    skip: bool
    reason: str | None = None  # "blacklist" | "cooldown" | "auto_reply_disabled" | None


@dataclass
class CommentFilter:
    """Stateful filter — holds per-user cooldown timestamps for a session."""

    _settings: dict[str, Any]
    _cooldown_map: dict[str, float] = field(default_factory=dict)

    def check(self, user_id: str, text: str) -> FilterResult:
        """Return FilterResult(skip=True, reason=...) if comment should be skipped."""
        # 1. auto_reply_enabled gate
        if not self._settings.get("auto_reply_enabled", True):
            return FilterResult(skip=True, reason="auto_reply_disabled")

        # 2. Blacklist
        blacklist = self._settings.get("blacklist_keywords", [])
        text_lower = text.lower()
        if any(kw.lower() in text_lower for kw in blacklist):
            logger.debug("Blacklist hit for user %s: %s", user_id, text[:40])
            return FilterResult(skip=True, reason="blacklist")

        # 3. Per-user cooldown
        cooldown_secs = self._settings.get("user_cooldown_seconds", 60)
        last_reply = self._cooldown_map.get(user_id)
        if last_reply is not None and (time.time() - last_reply) < cooldown_secs:
            logger.debug("Cooldown hit for user %s", user_id)
            return FilterResult(skip=True, reason="cooldown")

        return FilterResult(skip=False)

    def update_cooldown(self, user_id: str) -> None:
        """Record that we replied to this user right now."""
        self._cooldown_map[user_id] = time.time()
