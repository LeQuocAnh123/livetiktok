"""
Shared session state — single source of truth for live session globals.

This module exists to avoid circular imports between ws.py and sessions.py.
Both modules import from here instead of importing each other.
"""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.core.listener import TikTokListener
    from app.core.replier import Replier
    from app.core.pipeline import Pipeline


class SessionState:
    """Singleton holding the active session state."""

    def __init__(self) -> None:
        self.active_session_id: Optional[str] = None
        self.active_listener: Optional["TikTokListener"] = None
        self.active_replier: Optional["Replier"] = None
        self.active_pipeline: Optional["Pipeline"] = None
        self.active_task: Optional[Any] = None  # asyncio.Task
        self.bot_paused: bool = False
        self.reply_count: int = 0

    def reset(self) -> None:
        """Reset all state to initial values."""
        self.active_session_id = None
        self.active_listener = None
        self.active_replier = None
        self.active_pipeline = None
        self.active_task = None
        self.bot_paused = False
        self.reply_count = 0


# Global singleton instance
session_state = SessionState()
