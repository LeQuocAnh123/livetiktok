"""Tests for security module."""

import pytest
from app.core.security import hash_password, verify_seller_password


def test_hash_password_returns_hash():
    """hash_password should return a bcrypt hash string."""
    password = "mysecretpassword"
    hashed = hash_password(password)
    assert hashed != password
    assert hashed.startswith("$2b$")  # bcrypt prefix


def test_verify_seller_password_correct():
    """verify_seller_password returns True for correct password."""
    password = "mysecretpassword"
    hashed = hash_password(password)
    assert verify_seller_password(password, hashed) is True


def test_verify_seller_password_incorrect():
    """verify_seller_password returns False for incorrect password."""
    hashed = hash_password("correctpassword")
    assert verify_seller_password("wrongpassword", hashed) is False
