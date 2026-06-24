"""屏幕坐标级 GUI 操作（配合 VLM 使用）."""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any

import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15


def _screen_size() -> tuple[int, int]:
    size = pyautogui.size()
    return int(size.width), int(size.height)


def _to_pixel(x: float, y: float) -> tuple[int, int]:
    """VLM 返回 0–1000 归一化坐标，或已是像素坐标。"""
    sw, sh = _screen_size()
    if 0 <= x <= 1000 and 0 <= y <= 1000:
        return int(x / 1000 * sw), int(y / 1000 * sh)
    return int(x), int(y)


def click(params: dict[str, Any]) -> dict[str, Any]:
    x, y = _to_pixel(float(params.get("x", 0)), float(params.get("y", 0)))
    button = params.get("button", "left")
    pyautogui.click(x, y, button=button)
    return {"x": x, "y": y, "button": button}


def double_click(params: dict[str, Any]) -> dict[str, Any]:
    x, y = _to_pixel(float(params.get("x", 0)), float(params.get("y", 0)))
    pyautogui.doubleClick(x, y)
    return {"x": x, "y": y}


def scroll(params: dict[str, Any]) -> dict[str, Any]:
    clicks = int(params.get("clicks", params.get("scroll", -3)))
    x = params.get("x")
    y = params.get("y")
    if x is not None and y is not None:
        px, py = _to_pixel(float(x), float(y))
        pyautogui.scroll(clicks, x=px, y=py)
    else:
        pyautogui.scroll(clicks)
    return {"clicks": clicks}


def hotkey(params: dict[str, Any]) -> dict[str, Any]:
    keys = params.get("keys") or params.get("key")
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.replace("+", " ").split() if k.strip()]
    if not keys:
        raise ValueError("keys 不能为空")
    pyautogui.hotkey(*keys)
    return {"keys": keys}


def wait(params: dict[str, Any]) -> dict[str, Any]:
    seconds = float(params.get("seconds", 1))
    time.sleep(max(0.1, min(seconds, 10)))
    return {"seconds": seconds}


def encode_image_file(path: str | Path) -> str:
    data = Path(path).read_bytes()
    return base64.b64encode(data).decode("ascii")
