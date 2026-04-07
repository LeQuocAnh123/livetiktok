"""Security utilities for JWT and password verification."""

from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings


def create_access_token(subject: str) -> str:
    """Create a JWT access token for the given subject (username)."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> str | None:
    """
    Decode and verify a JWT token.
    Returns the subject (username) if valid, None otherwise.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None


def verify_password(plain_password: str, username: str) -> bool:
    """
    Verify password against configured admin credentials.
    Simple comparison — no hashing since credentials are from env vars.
    """
    settings = get_settings()
    return username == settings.admin_username and plain_password == settings.admin_password
