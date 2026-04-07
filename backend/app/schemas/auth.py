"""Auth request/response schemas."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login credentials."""

    username: str
    password: str


class SellerResponse(BaseModel):
    """Current seller info returned after login."""

    id: str
    username: str
    name: str
    tiktok_unique_id: str

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    """DEPRECATED: Use SellerResponse instead."""

    username: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
