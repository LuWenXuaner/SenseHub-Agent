"""同 session 串行执行队列."""

from __future__ import annotations

import asyncio
from collections import defaultdict

_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def lane_lock(session_id: str) -> asyncio.Lock:
    key = session_id.strip() or "__default__"
    return _locks[key]
