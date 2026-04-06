from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Security
    secret_key: str

    # AI
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ai_reply_provider: str = "claude"
    ai_embed_provider: str = "openai"

    # TikTok
    tiktok_session_id: Optional[str] = None
    tiktok_target_idc: str = "useast1a"
    tiktok_sign_api_key: Optional[str] = None
    whitelist_authenticated_session_id_host: str = "tiktok.eulerstream.com"

    # App
    database_url: str = "sqlite+aiosqlite:///./app.db"
    chroma_path: str = "./chroma_data"
    reply_delay_min: int = 5
    reply_delay_max: int = 15
    # WebSocket monitor authentication — empty string disables auth check (dev only)
    ws_monitor_token: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Usage: from app.config import get_settings; settings = get_settings()
# Or use FastAPI dependency injection: Depends(get_settings)
# Do NOT import 'settings' directly at module level — use get_settings() for testability.
