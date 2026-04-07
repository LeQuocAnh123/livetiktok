"""Tests for comment filter — blacklist, per-user cooldown."""

import time

import pytest

DEFAULT_SETTINGS = {
    "tone": "friendly",
    "blacklist_keywords": ["spam", "xấu"],
    "reply_delay_min": 5,
    "reply_delay_max": 15,
    "user_cooldown_seconds": 60,
    "max_replies_per_session": 500,
    "auto_reply_enabled": True,
}


def make_filter(settings=None):
    from app.core.rag.filter import CommentFilter

    return CommentFilter(settings or DEFAULT_SETTINGS)


# --- Blacklist ---


def test_blacklist_blocks_comment():
    f = make_filter()
    result = f.check("user1", "đây là spam lắm")
    assert result.skip is True
    assert result.reason == "blacklist"


def test_blacklist_case_insensitive():
    f = make_filter()
    result = f.check("user1", "SPAM này")
    assert result.skip is True


def test_blacklist_allows_clean_comment():
    f = make_filter()
    result = f.check("user1", "Giá bao nhiêu vậy?")
    assert result.skip is False


# --- Intent ---

# --- Cooldown ---


def test_cooldown_blocks_repeat_within_window():
    f = make_filter(
        {"blacklist_keywords": [], "user_cooldown_seconds": 60, "auto_reply_enabled": True}
    )
    f.update_cooldown("user1")
    result = f.check("user1", "Giá bao nhiêu?")
    assert result.skip is True
    assert result.reason == "cooldown"


def test_cooldown_allows_after_expiry():
    f = make_filter(
        {"blacklist_keywords": [], "user_cooldown_seconds": 1, "auto_reply_enabled": True}
    )
    f.update_cooldown("user1")
    time.sleep(1.1)
    result = f.check("user1", "Giá bao nhiêu?")
    assert result.skip is False


def test_cooldown_allows_new_user():
    f = make_filter()
    result = f.check("brand-new-user", "Sản phẩm còn hàng không?")
    assert result.skip is False


# --- auto_reply_enabled ---


def test_auto_reply_disabled_blocks_all():
    settings = {**DEFAULT_SETTINGS, "auto_reply_enabled": False}
    f = make_filter(settings)
    result = f.check("user1", "Giá bao nhiêu?")
    assert result.skip is True
    assert result.reason == "auto_reply_disabled"
