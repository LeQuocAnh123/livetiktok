from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Security
    secret_key: str

    # AI
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ai_reply_provider: str = "claude"
    ai_embed_provider: str = "openai"

    # TikTok
    tiktok_session_id: str = ""
    tiktok_target_idc: str = "useast1a"
    tiktok_sign_api_key: str = ""
    whitelist_authenticated_session_id_host: str = "tiktok.eulerstream.com"

    # App
    database_url: str = "sqlite+aiosqlite:///./app.db"
    chroma_path: str = "./chroma_data"
    reply_delay_min: int = 5
    reply_delay_max: int = 15


settings = Settings()
