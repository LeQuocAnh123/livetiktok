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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "ai_reply_provider": settings.ai_reply_provider,
        "ai_embed_provider": settings.ai_embed_provider,
    }


from app.api.v1.sessions import router as sessions_router  # noqa: E402
app.include_router(sessions_router)

from app.api.v1.knowledge import router as knowledge_router  # noqa: E402
app.include_router(knowledge_router)

from app.api.ws import router as ws_router  # noqa: E402
app.include_router(ws_router)
