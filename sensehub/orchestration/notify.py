"""任务状态 WebSocket 广播."""

from __future__ import annotations

from typing import Callable

from sensehub.models.schemas import TaskResponse

_listeners: list[Callable[[TaskResponse], None]] = []


def subscribe(listener: Callable[[TaskResponse], None]) -> None:
    _listeners.append(listener)


def notify(task: TaskResponse) -> None:
    for fn in _listeners:
        try:
            fn(task)
        except Exception:
            pass
