from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.session import LiveSession, SessionStatus
from app.schemas.session import SessionStatusResponse

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

# In-memory state: single active session (single-seller v1)
_active_session_id: str | None = None


@router.get("/status", response_model=SessionStatusResponse)
async def get_status(db: AsyncSession = Depends(get_db)):
    if _active_session_id is None:
        return SessionStatusResponse(connected=False, session=None)

    result = await db.execute(
        select(LiveSession).where(LiveSession.id == _active_session_id)
    )
    session = result.scalar_one_or_none()
    if session is None or session.status != SessionStatus.ACTIVE:
        return SessionStatusResponse(connected=False, session=None)

    return SessionStatusResponse(connected=True, session=session)
