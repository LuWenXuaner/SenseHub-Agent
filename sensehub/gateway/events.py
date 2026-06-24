"""Agent 运行时事件总线（供 WebSocket 推送）."""

from __future__ import annotations

from typing import Any, Callable

_listeners: list[Callable[[dict[str, Any]], None]] = []


def subscribe(listener: Callable[[dict[str, Any]], None]) -> None:
    if listener not in _listeners:
        _listeners.append(listener)


def unsubscribe(listener: Callable[[dict[str, Any]], None]) -> None:
    if listener in _listeners:
        _listeners.remove(listener)


def emit(event: dict[str, Any]) -> None:
    for listener in list(_listeners):
        try:
            listener(event)
        except Exception:
            continue
