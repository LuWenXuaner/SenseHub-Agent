"""增强 GUI 桌面操作：图像锚点匹配、拖拽、区域操作、自动重试."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import pyautogui
from PIL import ImageGrab

from sensehub.execution.tools.base import push_progress, tool_result, with_retry

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15


def _screen_size() -> tuple[int, int]:
    size = pyautogui.size()
    return int(size.width), int(size.height)


def _to_pixel(x: float, y: float) -> tuple[int, int]:
    sw, sh = _screen_size()
    if 0 <= x <= 1000 and 0 <= y <= 1000:
        return int(x / 1000 * sw), int(y / 1000 * sh)
    return int(x), int(y)


def _locate_image_on_screen(
    template_path: str,
    confidence: float = 0.8,
    region: tuple[int, int, int, int] | None = None,
) -> tuple[int, int] | None:
    try:
        import cv2
    except ImportError:
        raise RuntimeError("需要 opencv-python，请运行: pip install opencv-python-headless")

    template = cv2.imread(template_path)
    if template is None:
        raise FileNotFoundError(f"模板图片不存在: {template_path}")

    screenshot = np.array(ImageGrab.grab(bbox=region))
    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)

    h, w = template.shape[:2]
    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < confidence:
        return None

    center_x = max_loc[0] + w // 2
    center_y = max_loc[1] + h // 2
    if region:
        center_x += region[0]
        center_y += region[1]
    return int(center_x), int(center_y)


def click_image(params: dict[str, Any]) -> dict[str, Any]:
    template = str(params.get("template", "")).strip()
    if not template:
        raise ValueError("template 图片路径不能为空")
    confidence = float(params.get("confidence", 0.8))
    button = params.get("button", "left")
    retry = int(params.get("retry", 3))

    path = Path(template)
    if not path.is_absolute():
        from sensehub.settings import get_settings
        path = get_settings().screenshots_dir / "templates" / path
    template_str = str(path)

    for attempt in range(retry):
        pos = _locate_image_on_screen(template_str, confidence=confidence)
        if pos:
            x, y = pos
            pyautogui.click(x, y, button=button)
            return tool_result(
                True, f"已点击图片匹配位置 ({x}, {y})",
                data={"x": x, "y": y, "button": button, "template": template, "confidence": confidence},
            )
        if attempt < retry - 1:
            push_progress(f"未匹配到图片，第 {attempt + 2}/{retry} 次重试...", progress=(attempt + 1) / retry)
            time.sleep(1.0)
    return tool_result(False, f"未能在屏幕上匹配到图片: {template}（置信度 >= {confidence}）")


def locate_image(params: dict[str, Any]) -> dict[str, Any]:
    template = str(params.get("template", "")).strip()
    if not template:
        raise ValueError("template 图片路径不能为空")
    confidence = float(params.get("confidence", 0.8))
    region_raw = params.get("region")

    region = None
    if region_raw and len(region_raw) == 4:
        region = tuple(int(v) for v in region_raw)

    path = Path(template)
    if not path.is_absolute():
        from sensehub.settings import get_settings
        path = get_settings().screenshots_dir / "templates" / path

    pos = _locate_image_on_screen(str(path), confidence=confidence, region=region)
    if pos:
        return tool_result(True, f"图片位于 ({pos[0]}, {pos[1]})", data={"x": pos[0], "y": pos[1], "confidence": confidence})
    return tool_result(False, f"未匹配到图片: {template}")


def click(params: dict[str, Any]) -> dict[str, Any]:
    x, y = _to_pixel(float(params.get("x", 0)), float(params.get("y", 0)))
    button = params.get("button", "left")
    clicks = int(params.get("clicks", 1))
    pyautogui.click(x, y, button=button, clicks=clicks)
    return tool_result(True, f"已点击 ({x}, {y})", data={"x": x, "y": y, "button": button, "clicks": clicks})


def double_click(params: dict[str, Any]) -> dict[str, Any]:
    x, y = _to_pixel(float(params.get("x", 0)), float(params.get("y", 0)))
    pyautogui.doubleClick(x, y)
    return tool_result(True, f"已双击 ({x}, {y})", data={"x": x, "y": y})


def right_click(params: dict[str, Any]) -> dict[str, Any]:
    x, y = _to_pixel(float(params.get("x", 0)), float(params.get("y", 0)))
    pyautogui.rightClick(x, y)
    return tool_result(True, f"已右键点击 ({x}, {y})", data={"x": x, "y": y})


def drag(params: dict[str, Any]) -> dict[str, Any]:
    start_x, start_y = _to_pixel(float(params.get("start_x", 0)), float(params.get("start_y", 0)))
    end_x, end_y = _to_pixel(float(params.get("end_x", 0)), float(params.get("end_y", 0)))
    duration = float(params.get("duration", 0.3))
    button = params.get("button", "left")
    pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)
    return tool_result(
        True, f"已拖拽从 ({start_x}, {start_y}) 到 ({end_x}, {end_y})",
        data={"start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y},
    )


def scroll(params: dict[str, Any]) -> dict[str, Any]:
    clicks = int(params.get("clicks", params.get("scroll", -3)))
    x = params.get("x")
    y = params.get("y")
    if x is not None and y is not None:
        px, py = _to_pixel(float(x), float(y))
        pyautogui.scroll(clicks, x=px, y=py)
    else:
        pyautogui.scroll(clicks)
    return tool_result(True, data={"clicks": clicks})


def type_text(params: dict[str, Any]) -> dict[str, Any]:
    text = params.get("text", "")
    if not text:
        raise ValueError("text 不能为空")
    interval = float(params.get("interval", 0.02))
    pyautogui.write(text, interval=interval)
    return tool_result(True, f"已输入 {len(text)} 个字符", data={"text": text, "length": len(text), "method": "write"})


def press_key(params: dict[str, Any]) -> dict[str, Any]:
    keys = params.get("keys") or params.get("key")
    if isinstance(keys, str):
        if "+" in keys or " " in keys:
            parts = [k.strip() for k in keys.replace("+", " ").split() if k.strip()]
            pyautogui.hotkey(*parts)
            return tool_result(True, f"已按下组合键: {parts}", data={"keys": parts})
        pyautogui.press(keys)
        return tool_result(True, f"已按下: {keys}", data={"key": keys})
    if isinstance(keys, list) and keys:
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
        return tool_result(True, data={"keys": keys})
    raise ValueError("keys 不能为空")


def hotkey(params: dict[str, Any]) -> dict[str, Any]:
    keys = params.get("keys") or params.get("key")
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.replace("+", " ").split() if k.strip()]
    if not keys:
        raise ValueError("keys 不能为空")
    pyautogui.hotkey(*keys)
    return tool_result(True, f"已执行快捷键: {keys}", data={"keys": keys})


def move_to(params: dict[str, Any]) -> dict[str, Any]:
    x, y = _to_pixel(float(params.get("x", 0)), float(params.get("y", 0)))
    duration = float(params.get("duration", 0.2))
    pyautogui.moveTo(x, y, duration=duration)
    return tool_result(True, f"鼠标已移动到 ({x}, {y})", data={"x": x, "y": y})


def get_position(params: dict[str, Any]) -> dict[str, Any]:
    _ = params
    x, y = pyautogui.position()
    return tool_result(True, data={"x": int(x), "y": int(y)})


def wait(params: dict[str, Any]) -> dict[str, Any]:
    seconds = float(params.get("seconds", 1))
    sleep_time = max(0.1, min(seconds, 30))
    time.sleep(sleep_time)
    return tool_result(True, data={"seconds": sleep_time})
