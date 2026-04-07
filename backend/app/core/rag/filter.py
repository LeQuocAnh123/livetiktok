"""Comment filter: blacklist keywords, per-user cooldown."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


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

    def reset_cooldown(self, user_id: str) -> None:
        """Remove user from cooldown map (e.g. for negative sentiment priority)."""
        self._cooldown_map.pop(user_id, None)

    def seed_cooldowns(self, cooldown_map: dict[str, float]) -> None:
        """Populate cooldown map from persisted data (e.g. MessageLog timestamps).

        Used when restarting a session so cooldowns survive across restarts.
        ``cooldown_map`` maps user_id → epoch timestamp of their last reply.
        """
        self._cooldown_map.update(cooldown_map)
