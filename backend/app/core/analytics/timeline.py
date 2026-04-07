"""Time-bucketed activity computation for live sessions.

Bucketing done in Python (not SQL) because SQLite date/time
functions are limited and data fits comfortably in memory.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import math


@dataclass
class TimelineBucket:
    bucket_start: datetime
    bucket_end: datetime
    comment_count: int = 0
    reply_count: int = 0
    gift_count: int = 0
    gift_diamonds: int = 0


def compute_timeline(
    session_start: datetime,
    session_end: datetime | None,
    messages: list,
    gifts: list,
    bucket_minutes: int = 5,
) -> list[TimelineBucket]:
    """Compute time-bucketed activity for a session.

    Args:
        session_start: When the live session started.
        session_end: When the session ended (None if still active).
        messages: MessageLog rows (need .created_at, .reply attributes).
        gifts: GiftLog rows (need .created_at, .total_diamonds attributes).
        bucket_minutes: Width of each bucket in minutes.

    Returns:
        Sorted list of TimelineBucket objects.
    """
    bucket_seconds = bucket_minutes * 60

    # Determine effective end time
    effective_end = session_end
    if effective_end is None:
        event_times: list[datetime] = []
        for m in messages:
            event_times.append(m.created_at)
        for g in gifts:
            event_times.append(g.created_at)
        if event_times:
            effective_end = max(event_times)
        else:
            effective_end = session_start + timedelta(seconds=bucket_seconds)

    # Calculate number of buckets
    total_seconds = (effective_end - session_start).total_seconds()
    num_buckets = max(1, math.ceil(total_seconds / bucket_seconds))

    # Create empty buckets
    buckets: list[TimelineBucket] = []
    for i in range(num_buckets):
        b_start = session_start + timedelta(seconds=i * bucket_seconds)
        b_end = session_start + timedelta(seconds=(i + 1) * bucket_seconds)
        buckets.append(TimelineBucket(bucket_start=b_start, bucket_end=b_end))

    # Assign messages to buckets
    for msg in messages:
        offset = (msg.created_at - session_start).total_seconds()
        idx = min(int(offset // bucket_seconds), num_buckets - 1)
        if idx < 0:
            idx = 0
        buckets[idx].comment_count += 1
        if msg.reply is not None:
            buckets[idx].reply_count += 1

    # Assign gifts to buckets
    for gift in gifts:
        offset = (gift.created_at - session_start).total_seconds()
        idx = min(int(offset // bucket_seconds), num_buckets - 1)
        if idx < 0:
            idx = 0
        buckets[idx].gift_count += 1
        buckets[idx].gift_diamonds += gift.total_diamonds

    return buckets
