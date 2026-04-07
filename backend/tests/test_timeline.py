"""Unit tests for timeline bucketing."""

from datetime import datetime, timedelta

import pytest

from app.core.analytics.timeline import TimelineBucket, compute_timeline


def _make_msg(created_at: datetime, reply: str | None = "reply"):
    """Create a minimal message-like object for testing."""

    class FakeMsg:
        pass

    m = FakeMsg()
    m.created_at = created_at
    m.reply = reply
    return m


def _make_gift(created_at: datetime, total_diamonds: int = 10):
    """Create a minimal gift-like object for testing."""

    class FakeGift:
        pass

    g = FakeGift()
    g.created_at = created_at
    g.total_diamonds = total_diamonds
    return g


class TestComputeTimeline:
    def test_single_bucket_for_short_session(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 10, 4, 0)
        msgs = [_make_msg(start + timedelta(minutes=1))]
        gifts = [_make_gift(start + timedelta(minutes=2), total_diamonds=50)]
        result = compute_timeline(start, end, msgs, gifts, bucket_minutes=5)
        assert len(result) == 1
        assert result[0].comment_count == 1
        assert result[0].gift_count == 1
        assert result[0].gift_diamonds == 50

    def test_multiple_buckets(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 10, 12, 0)
        msgs = [
            _make_msg(start + timedelta(minutes=1)),
            _make_msg(start + timedelta(minutes=3)),
            _make_msg(start + timedelta(minutes=7)),
        ]
        gifts = [
            _make_gift(start + timedelta(minutes=11), total_diamonds=100),
        ]
        result = compute_timeline(start, end, msgs, gifts, bucket_minutes=5)
        assert len(result) == 3
        assert result[0].comment_count == 2
        assert result[1].comment_count == 1
        assert result[2].comment_count == 0
        assert result[2].gift_count == 1
        assert result[2].gift_diamonds == 100

    def test_empty_session(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 10, 10, 0)
        result = compute_timeline(start, end, [], [], bucket_minutes=5)
        assert len(result) == 2
        for b in result:
            assert b.comment_count == 0
            assert b.reply_count == 0
            assert b.gift_count == 0
            assert b.gift_diamonds == 0

    def test_session_without_end_uses_last_event(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        last_msg_time = datetime(2026, 1, 1, 10, 8, 0)
        msgs = [_make_msg(last_msg_time)]
        result = compute_timeline(start, None, msgs, [], bucket_minutes=5)
        assert len(result) == 2
        assert result[1].comment_count == 1

    def test_session_without_end_and_no_events(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        result = compute_timeline(start, None, [], [], bucket_minutes=5)
        assert len(result) == 1
        assert result[0].comment_count == 0

    def test_reply_count_tracks_messages_with_reply(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 10, 5, 0)
        msgs = [
            _make_msg(start + timedelta(minutes=1), reply="answered"),
            _make_msg(start + timedelta(minutes=2), reply=None),
            _make_msg(start + timedelta(minutes=3), reply="answered"),
        ]
        result = compute_timeline(start, end, msgs, [], bucket_minutes=5)
        assert result[0].comment_count == 3
        assert result[0].reply_count == 2

    def test_bucket_boundaries(self):
        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 10, 10, 0)
        result = compute_timeline(start, end, [], [], bucket_minutes=5)
        assert result[0].bucket_start == start
        assert result[0].bucket_end == start + timedelta(minutes=5)
        assert result[1].bucket_start == start + timedelta(minutes=5)
        assert result[1].bucket_end == start + timedelta(minutes=10)
