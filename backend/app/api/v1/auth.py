"""Authentication API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import create_access_token, decode_access_token, verify_seller_password
from app.database import get_db
from app.models.seller import Seller
from app.schemas.auth import LoginRequest, MessageResponse, SellerResponse

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


@router.post("/login", response_model=SellerResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate seller and set httpOnly cookie."""
    # Find seller by username
    result = await db.execute(select(Seller).where(Seller.username == body.username))
    seller = result.scalar_one_or_none()

    if seller is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not seller.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")

    if not verify_seller_password(body.password, seller.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(seller.id)
    _set_auth_cookie(response, token)
    logger.info("Seller logged in: %s (id=%s)", seller.username, seller.id)

    return SellerResponse(
        id=seller.id,
        username=seller.username,
        name=seller.name,
        tiktok_unique_id=seller.tiktok_unique_id,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    """Clear auth cookie."""
    _clear_auth_cookie(response)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=SellerResponse)
async def get_current_user_info(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated seller info."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    seller_id = payload.get("sub")
    seller = await db.get(Seller, seller_id)
    if not seller or not seller.is_active:
        raise HTTPException(status_code=401, detail="Account not found or disabled")

    return SellerResponse(
        id=seller.id,
        username=seller.username,
        name=seller.name,
        tiktok_unique_id=seller.tiktok_unique_id,
    )


async def get_current_seller(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Seller:
    """
    Dependency to get the current authenticated seller.
    Use with Depends(get_current_seller) on protected routes.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    seller_id = payload.get("sub")
    seller = await db.get(Seller, seller_id)
    if not seller or not seller.is_active:
        raise HTTPException(status_code=401, detail="Account not found or disabled")

    return seller


# DEPRECATED: Backward compatibility alias
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> str:
    """DEPRECATED: Use get_current_seller instead. Returns seller_id."""
    seller = await get_current_seller(request, db)
    return seller.id
