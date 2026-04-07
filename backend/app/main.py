import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import create_tables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def lifespan(app: FastAPI):
    settings = get_settings()
    # Set TikTok env var required for send_room_chat
    os.environ.setdefault(
        "WHITELIST_AUTHENTICATED_SESSION_ID_HOST",
        settings.whitelist_authenticated_session_id_host,
    )
    logger.info("Starting up — creating DB tables if needed")
    await create_tables()
    logger.info("Database ready")
    yield
    logger.info("Shutting down")


app = FastAPI(title="TikTok Live AI Bot", version="0.1.0", lifespan=lifespan)

# Parse CORS origins from config (comma-separated)
settings = get_settings()
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    settings = get_settings()
    results: dict = {
        "status": "ok",
        "ai_provider": settings.ai_reply_provider,
        "db": "unknown",
        "chroma": "unknown",
    }

    # Check DB
    try:
        from sqlalchemy import text
        from app.database import _get_engine

        async with _get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        results["db"] = "ok"
    except Exception as exc:
        results["db"] = f"error: {exc}"
        results["status"] = "degraded"

    # Check ChromaDB
    try:
        from app.core.rag.retriever import _get_client

        _get_client().heartbeat()
        results["chroma"] = "ok"
    except Exception as exc:
        results["chroma"] = f"error: {exc}"
        results["status"] = "degraded"

    return results


from app.api.v1.sessions import router as sessions_router  # noqa: E402

app.include_router(sessions_router)

from app.api.v1.knowledge import router as knowledge_router  # noqa: E402

app.include_router(knowledge_router)

from app.api.v1.settings import router as settings_router  # noqa: E402

app.include_router(settings_router)

from app.api.ws import router as ws_router  # noqa: E402

app.include_router(ws_router)

from app.api.v1.analytics import router as analytics_router  # noqa: E402

app.include_router(analytics_router)

from app.api.v1.auth import router as auth_router  # noqa: E402

app.include_router(auth_router)
