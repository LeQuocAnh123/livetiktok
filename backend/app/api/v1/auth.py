"""Authentication API endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Request, Response, Depends

from app.config import get_settings
from app.core.security import create_access_token, decode_access_token, verify_password
from app.schemas.auth import LoginRequest, MessageResponse, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_auth_cookie(response: Response, token: str) -> None:
    """Set the auth cookie with appropriate settings."""
    settings = get_settings()
    max_age = settings.jwt_expire_hours * 3600
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=max_age,
    )


def _clear_auth_cookie(response: Response) -> None:
    """Clear the auth cookie."""
    response.delete_cookie(key="access_token")


@router.post("/login", response_model=UserResponse)
async def login(body: LoginRequest, response: Response):
    """Authenticate user and set httpOnly cookie."""
    if not verify_password(body.password, body.username):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(body.username)
    _set_auth_cookie(response, token)
    logger.info("User logged in: %s", body.username)
    return UserResponse(username=body.username)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    """Clear auth cookie."""
    _clear_auth_cookie(response)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(request: Request):
    """Get current authenticated user info."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    username = decode_access_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return UserResponse(username=username)


async def get_current_user(request: Request) -> str:
    """
    Dependency to get the current authenticated user.
    Use with Depends(get_current_user) on protected routes.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    username = decode_access_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return username
