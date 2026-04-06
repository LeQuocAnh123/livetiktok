"""Backup & Restore endpoints for SQLite database."""
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import get_settings
from app.database import _get_engine

router = APIRouter(prefix="/api/v1/backup", tags=["backup"])


def _db_path() -> Path:
    url = get_settings().database_url  # sqlite+aiosqlite:///./app.db
    # Extract file path from URL
    path_str = url.split("///")[-1]
    return Path(path_str)


@router.get("/download")
async def download_backup():
    """Download the current SQLite database file."""
    db = _db_path()
    if not db.exists():
        raise HTTPException(status_code=404, detail="Database file not found")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.db"

    # Copy to a temp file so we serve a snapshot, not the live file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    shutil.copy2(db, tmp.name)
    tmp.close()

    return FileResponse(
        path=tmp.name,
        media_type="application/octet-stream",
        filename=filename,
    )


@router.post("/restore")
async def restore_backup(file: UploadFile):
    """Replace the current database with an uploaded backup file."""
    if not (file.filename or "").endswith(".db"):
        raise HTTPException(status_code=400, detail="Only .db files are supported")

    db = _db_path()

    content = await file.read()
    if len(content) < 100:
        raise HTTPException(status_code=400, detail="File quá nhỏ, có thể không phải SQLite database")

    # Validate SQLite magic bytes
    if not content.startswith(b"SQLite format 3"):
        raise HTTPException(status_code=400, detail="File không phải SQLite database hợp lệ")

    # Dispose all connections before replacing the file
    engine = _get_engine()
    await engine.dispose()

    # Backup current db before overwriting
    if db.exists():
        backup_path = db.with_suffix(f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(db, backup_path)

    db.write_bytes(content)

    return {"message": "Database restored successfully. Please restart the server to reconnect."}
