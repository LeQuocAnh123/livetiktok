"""Auth request/response schemas."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login credentials."""

    username: str
    password: str


class UserResponse(BaseModel):
    """Current user info."""

    username: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
