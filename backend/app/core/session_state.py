"""
Shared session state — single source of truth for live session globals.

This module exists to avoid circular imports between ws.py and sessions.py.
Both modules import from here instead of importing each other.
"""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.core.rag.pipeline import RAGPipeline
    from app.core.tiktok.listener import LiveListener
    from app.core.tiktok.replier import Replier


class SessionState:
    """Holds the active session state for a single seller."""

    def __init__(self, seller_id: str) -> None:
        self.seller_id: str = seller_id
        self.active_session_id: Optional[str] = None
        self.active_listener: Optional["LiveListener"] = None
        self.active_replier: Optional["Replier"] = None
        self.active_pipeline: Optional["RAGPipeline"] = None
        self.active_task: Optional[Any] = None  # asyncio.Task
        self.bot_paused: bool = False
        self.reply_count: int = 0

    def reset(self) -> None:
        """Reset all state to initial values (keeps seller_id)."""
        self.active_session_id = None
        self.active_listener = None
        self.active_replier = None
        self.active_pipeline = None
        self.active_task = None
        self.bot_paused = False
        self.reply_count = 0


# Multi-tenant state dict keyed by seller_id
session_states: dict[str, SessionState] = {}


def get_session_state(seller_id: str) -> SessionState:
    """Get or create session state for a seller."""
    if seller_id not in session_states:
        session_states[seller_id] = SessionState(seller_id)
    return session_states[seller_id]


# DEPRECATED: Keep for backward compatibility during migration
session_state = SessionState("legacy")
