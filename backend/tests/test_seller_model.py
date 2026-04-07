"""Tests for Seller model auth fields."""

import pytest
from app.models.seller import Seller


def test_seller_has_auth_fields():
    """Seller model should have username, password_hash, is_active fields."""
    seller = Seller(
        name="Test Shop",
        username="testshop",
        password_hash="hashed_password",
        is_active=True,
        tiktok_unique_id="@testshop",
        tiktok_session_id_encrypted="enc_session",
        tiktok_target_idc_encrypted="enc_idc",
    )
    assert seller.username == "testshop"
    assert seller.password_hash == "hashed_password"
    assert seller.is_active is True


@pytest.mark.asyncio
async def test_seller_is_active_defaults_true_in_db(db_session):
    """is_active defaults to True when committed to database."""
    seller = Seller(
        name="Test Shop",
        username="testshop_db",
        password_hash="hashed",
        tiktok_unique_id="@testshop",
        tiktok_session_id_encrypted="enc",
        tiktok_target_idc_encrypted="enc",
    )
    db_session.add(seller)
    await db_session.commit()
    await db_session.refresh(seller)
    assert seller.is_active is True
