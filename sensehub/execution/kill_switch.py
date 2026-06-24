"""全局 Kill Switch."""

from __future__ import annotations

import threading

_lock = threading.Lock()
_active = False


def is_killed() -> bool:
    with _lock:
        return _active


def activate() -> None:
    with _lock:
        global _active
        _active = True


def reset() -> None:
    with _lock:
        global _active
        _active = False
