"""增强屏幕截图：全屏 / 区域 / 窗口截图、Base64 编码、压缩."""

from __future__ import annotations

import base64
import io
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import mss
from PIL import Image

from sensehub.execution.tools.base import push_progress, tool_result
from sensehub.settings import get_settings


def _compress_image(image: Image.Image, quality: int = 85, max_size: tuple[int, int] | None = None) -> Image.Image:
    if max_size:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return image


def _image_to_base64(image: Image.Image, fmt: str = "JPEG", quality: int = 85) -> str:
    buf = io.BytesIO()
    image.save(buf, format=fmt, quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _save_image(image: Image.Image, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return str(path)


def capture_fullscreen(params: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    out_dir = settings.screenshots_dir
    name = f"full_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
    path = out_dir / name

    return_base64 = bool(params.get("base64", False))
    quality = int(params.get("quality", 85))
    max_width = params.get("max_width")
    max_height = params.get("max_height")

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    max_size = None
    if max_width and max_height:
        max_size = (int(max_width), int(max_height))
    if max_size or quality < 100:
        img = _compress_image(img, quality=quality, max_size=max_size)

    saved_path = _save_image(img, path)

    result_data: dict[str, Any] = {
        "screenshot_path": saved_path,
        "mode": "fullscreen",
        "width": img.width,
        "height": img.height,
        "format": "PNG",
    }

    if return_base64:
        fmt = "JPEG" if quality < 100 else "PNG"
        result_data["base64"] = _image_to_base64(img, fmt=fmt, quality=quality)
        result_data["base64_format"] = fmt

    return tool_result(True, f"全屏截图已保存: {saved_path}", data=result_data)


def capture_region(params: dict[str, Any]) -> dict[str, Any]:
    left = int(params.get("left", 0))
    top = int(params.get("top", 0))
    width = int(params.get("width", 800))
    height = int(params.get("height", 600))

    if width <= 0 or height <= 0:
        raise ValueError("width 和 height 必须为正数")

    settings = get_settings()
    out_dir = settings.screenshots_dir
    name = f"region_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
    path = out_dir / name

    return_base64 = bool(params.get("base64", False))
    quality = int(params.get("quality", 85))

    with mss.mss() as sct:
        monitor = {"left": left, "top": top, "width": width, "height": height}
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    saved_path = _save_image(img, path)

    result_data: dict[str, Any] = {
        "screenshot_path": saved_path,
        "mode": "region",
        "left": left,
        "top": top,
        "width": img.width,
        "height": img.height,
    }

    if return_base64:
        fmt = "JPEG" if quality < 100 else "PNG"
        img_comp = _compress_image(img, quality=quality) if quality < 100 else img
        result_data["base64"] = _image_to_base64(img_comp, fmt=fmt, quality=quality)
        result_data["base64_format"] = fmt

    return tool_result(True, f"区域截图已保存: {saved_path}", data=result_data)


def capture_window(params: dict[str, Any]) -> dict[str, Any]:
    import win32gui
    import win32con

    title = str(params.get("title", "")).strip()
    settings = get_settings()
    out_dir = settings.screenshots_dir
    name = f"window_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
    path = out_dir / name

    return_base64 = bool(params.get("base64", False))
    quality = int(params.get("quality", 85))

    def _enum_windows(hwnd, _):
        nonlocal target_hwnd
        if not win32gui.IsWindowVisible(hwnd):
            return
        if title and title.lower() in win32gui.GetWindowText(hwnd).strip().lower():
            target_hwnd = hwnd
            return

    target_hwnd = None
    if title:
        win32gui.EnumWindows(_enum_windows, None)
        if not target_hwnd:
            return tool_result(False, f"未找到包含标题 '{title}' 的窗口")
    else:
        target_hwnd = win32gui.GetForegroundWindow()
        if not target_hwnd:
            return tool_result(False, "无法获取前台窗口句柄")
        title = win32gui.GetWindowText(target_hwnd).strip()

    try:
        left, top, right, bottom = win32gui.GetWindowRect(target_hwnd)
        win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        time.sleep(0.2)
    except Exception:
        pass
    # re-read rect after restore
    left, top, right, bottom = win32gui.GetWindowRect(target_hwnd)
    width = max(1, right - left)
    height = max(1, bottom - top)

    with mss.mss() as sct:
        monitor = {"left": left, "top": top, "width": width, "height": height}
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    saved_path = _save_image(img, path)

    result_data: dict[str, Any] = {
        "screenshot_path": saved_path,
        "mode": "window",
        "window_title": title,
        "left": left,
        "top": top,
        "width": img.width,
        "height": img.height,
    }

    if return_base64:
        fmt = "JPEG" if quality < 100 else "PNG"
        img_comp = _compress_image(img, quality=quality) if quality < 100 else img
        result_data["base64"] = _image_to_base64(img_comp, fmt=fmt, quality=quality)
        result_data["base64_format"] = fmt

    return tool_result(True, f"窗口截图已保存: {saved_path}（窗口: {title}）", data=result_data)


def run(params: dict[str, Any]) -> dict[str, Any]:
    mode = params.get("mode", "fullscreen")
    if mode == "active_window":
        return capture_window({**params, "title": params.get("title", "")})
    elif mode == "region":
        return capture_region(params)
    else:
        return capture_fullscreen(params)
