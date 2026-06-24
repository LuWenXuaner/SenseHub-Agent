"""虚拟屏实时会话：腕部 → 鼠标移动，举手 → 点击."""

from __future__ import annotations

import asyncio
import threading
import time

from sensehub.perception.camera import CameraService
from sensehub.perception.gesture import GestureDetector
from sensehub.perception.overlay import VirtualMouseOverlay
from sensehub.perception.virtual_screen import get_calibration, map_camera_to_screen


class VirtualScreenSession:
    _lock = threading.Lock()
    _active = False
    _show_keyboard = False
    _last_click = 0.0
    _last_x = 0.0
    _last_y = 0.0
    _last_virtual_x = 0.0
    _last_virtual_y = 0.0
    _last_mouse_x = 0.0
    _last_mouse_y = 0.0
    _manual_override_until = 0.0
    _manual_override_extend_sec = 15.0
    _manual_drift_threshold = 36.0

    @classmethod
    def status(cls) -> dict:
        cal = get_calibration()
        now = time.time()
        return {
            "active": cls._active,
            "calibrated": cal.get("calibrated", False),
            "show_keyboard": cls._show_keyboard,
            "overlay": VirtualMouseOverlay.get().running,
            "pointer": {"x": cls._last_x, "y": cls._last_y},
            "manual_override": now < cls._manual_override_until,
        }

    @classmethod
    def start(cls) -> dict:
        cal = get_calibration()
        if not cal.get("calibrated"):
            raise RuntimeError("请先完成虚拟屏校准")
        cam = CameraService.get()
        if not cam.running:
            cam.start()
        GestureDetector.get().ensure_loaded()
        VirtualMouseOverlay.get().start()
        with cls._lock:
            cls._active = True
            cls._manual_override_until = 0.0
        return cls.status()

    @classmethod
    def stop(cls) -> dict:
        with cls._lock:
            cls._active = False
            cls._show_keyboard = False
            cls._manual_override_until = 0.0
        VirtualMouseOverlay.get().stop()
        return cls.status()

    @classmethod
    def toggle_keyboard(cls, enabled: bool | None = None) -> dict:
        with cls._lock:
            cls._show_keyboard = not cls._show_keyboard if enabled is None else enabled
        return cls.status()

    @classmethod
    def is_active(cls) -> bool:
        return cls._active

    @classmethod
    async def tick(cls) -> dict | None:
        if not cls._active:
            return None
        loop = asyncio.get_running_loop()
        cam = CameraService.get()
        frame = await loop.run_in_executor(None, cam.read)
        if frame is None:
            return None

        def _process():
            import pyautogui

            tip = GestureDetector.get().fingertip_for_virtual_screen(frame)
            gestures = GestureDetector.get().detect(frame)
            payload: dict = {"type": "pointer"}
            now = time.time()

            # 真实鼠标优先：若检测到鼠标位置明显偏离上次虚拟控制点，
            # 判定为用户手动接管，短时间内暂停手势接管。
            pos = pyautogui.position()
            mx, my = float(pos.x), float(pos.y)

            if cls._last_virtual_x or cls._last_virtual_y:
                drift = abs(mx - cls._last_virtual_x) + abs(my - cls._last_virtual_y)
                if drift > cls._manual_drift_threshold:
                    cls._manual_override_until = now + cls._manual_override_extend_sec

            manual_override = now < cls._manual_override_until
            if manual_override:
                mouse_delta = abs(mx - cls._last_mouse_x) + abs(my - cls._last_mouse_y)
                if mouse_delta > 2:
                    cls._manual_override_until = now + cls._manual_override_extend_sec
                    manual_override = True

            cls._last_mouse_x, cls._last_mouse_y = mx, my
            payload["manual_override"] = manual_override

            if tip:
                mapped = map_camera_to_screen(tip[0], tip[1])
                if mapped:
                    sx, sy = mapped
                    if manual_override:
                        # 手动接管期间，仅显示真实鼠标位置，不抢控制权
                        cls._last_x, cls._last_y = mx, my
                        VirtualMouseOverlay.get().update(mx, my, clicked=False)
                    else:
                        pyautogui.moveTo(int(sx), int(sy), duration=0)
                        VirtualMouseOverlay.get().update(sx, sy, clicked=False)
                        cls._last_virtual_x, cls._last_virtual_y = sx, sy
                        cls._last_x, cls._last_y = sx, sy
                    payload.update({"screen_x": sx, "screen_y": sy, "camera_x": tip[0], "camera_y": tip[1]})
            for g in gestures:
                if g.get("gesture") == "hand_raised" and g.get("confidence", 0) > 0.55 and not manual_override:
                    if now - cls._last_click > 1.2:
                        cls._last_click = now
                        pyautogui.click()
                        VirtualMouseOverlay.get().update(cls._last_x, cls._last_y, clicked=True)
                        payload["clicked"] = True
                    break
            return payload

        return await loop.run_in_executor(None, _process)

    @classmethod
    def type_text(cls, text: str) -> None:
        import pyautogui

        if text.isascii():
            pyautogui.typewrite(text, interval=0.02)
        else:
            import pyperclip

            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")

    @classmethod
    def press_key(cls, key: str) -> None:
        import pyautogui

        pyautogui.press(key)
