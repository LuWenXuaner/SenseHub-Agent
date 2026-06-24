"""虚拟屏工具（由规划脑选择，禁止正则捷径）."""

from __future__ import annotations

from typing import Any

from sensehub.licensing.tier import feature_enabled
from sensehub.perception.virtual_session import VirtualScreenSession


def virtual_screen_start(params: dict[str, Any]) -> dict[str, Any]:
    if not feature_enabled("virtual_screen"):
        raise RuntimeError("虚拟屏功能需要 Max 档位")
    status = VirtualScreenSession.start()
    return {"action": "virtual_screen_start", "message": "虚拟屏已开启", "status": status}


def virtual_screen_stop(params: dict[str, Any]) -> dict[str, Any]:
    if not feature_enabled("virtual_screen"):
        raise RuntimeError("虚拟屏功能需要 Max 档位")
    status = VirtualScreenSession.stop()
    return {"action": "virtual_screen_stop", "message": "虚拟屏已关闭", "status": status}


def virtual_keyboard_toggle(params: dict[str, Any]) -> dict[str, Any]:
    if not feature_enabled("virtual_screen"):
        raise RuntimeError("虚拟屏功能需要 Max 档位")
    enabled = bool(params.get("enabled", True))
    if enabled and not VirtualScreenSession.is_active():
        raise RuntimeError("请先打开虚拟屏")
    status = VirtualScreenSession.toggle_keyboard(enabled)
    return {
        "action": "virtual_keyboard_on" if enabled else "virtual_keyboard_off",
        "enabled": enabled,
        "status": status,
    }
