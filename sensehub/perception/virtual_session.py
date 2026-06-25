"""虚拟屏实时会话：视频画面 → 食指尖 → 鼠标."""

from __future__ import annotations

import asyncio
import logging
import threading
import time

from sensehub.perception.camera import CameraService
from sensehub.perception.config import get_perception_config
from sensehub.perception.finger_pointer import FingerPointer
from sensehub.perception.pointer import click_at_cursor, get_cursor_position, move_pointer
from sensehub.perception.overlay import VirtualMouseOverlay
from sensehub.perception.virtual_screen import get_calibration, get_mapping_mode, map_camera_to_screen, virtual_screen_ready

logger = logging.getLogger(__name__)


class VirtualScreenSession:
    _lock = threading.Lock()
    _active = False
    _show_keyboard = False
    _last_click = 0.0
    _last_x = 0.0
    _last_y = 0.0
    _smooth_x = 0.0
    _smooth_y = 0.0
    _smooth_ready = False
    _tick_idx = 0
    _suspend_until = 0.0
    _pointer_thread: threading.Thread | None = None
    _pointer_stop = threading.Event()
    _last_payload: dict | None = None
    _pinch_screen_locked = False
    _pinch_sx = 0.0
    _pinch_sy = 0.0

    @classmethod
    def _release_camera_if_idle(cls) -> None:
        """无预览客户端且虚拟屏已关时释放摄像头硬件."""
        try:
            from sensehub.api.camera_broadcaster import camera_broadcaster

            if camera_broadcaster.client_count > 0:
                return
        except Exception:
            pass
        if cls._active:
            return
        try:
            CameraService.get().stop()
        except Exception:
            logger.debug("camera stop skipped", exc_info=True)

    @classmethod
    def suspend_automation(cls, seconds: float) -> None:
        with cls._lock:
            cls._suspend_until = time.time() + max(0.5, float(seconds))

    @classmethod
    def _automation_suspended(cls) -> bool:
        return time.time() < cls._suspend_until

    @classmethod
    def status(cls) -> dict:
        cal = get_calibration()
        mode = get_mapping_mode()
        last = cls._last_payload or {}
        return {
            "active": cls._active,
            "calibrated": virtual_screen_ready(),
            "mapping_mode": mode,
            "homography_calibrated": bool(cal.get("calibrated")),
            "show_keyboard": cls._show_keyboard,
            "overlay": VirtualMouseOverlay.get().running,
            "pointer": {"x": cls._last_x, "y": cls._last_y},
            "automation_suspended": cls._automation_suspended(),
            "tracking": bool(last.get("tracking")),
            "pointer_error": last.get("error"),
            "screen_x": last.get("screen_x"),
            "screen_y": last.get("screen_y"),
        }

    @classmethod
    def _start_pointer_thread(cls) -> None:
        cls._pointer_stop.set()
        if cls._pointer_thread and cls._pointer_thread.is_alive():
            cls._pointer_thread.join(timeout=1.0)
        cls._pointer_stop.clear()
        cls._pointer_thread = threading.Thread(target=cls._pointer_loop, name="virtual-pointer", daemon=True)
        cls._pointer_thread.start()

    @classmethod
    def _pointer_loop(cls) -> None:
        interval = max(0.02, float(get_perception_config().get("virtual_pointer_interval_sec") or 0.033))
        while not cls._pointer_stop.is_set():
            if cls._active and not cls._automation_suspended():
                try:
                    payload = cls._tick_sync()
                    if payload:
                        cls._last_payload = payload
                except Exception:
                    logger.exception("virtual pointer tick failed")
            if cls._pointer_stop.wait(interval):
                break

    @classmethod
    def start(cls, *, _already_primed: bool = False) -> dict:
        if not virtual_screen_ready():
            mode = get_mapping_mode()
            if mode == "homography":
                raise RuntimeError("精细映射模式请先完成九点校准")
            raise RuntimeError("虚拟屏未就绪，请检查感知配置")
        cam = CameraService.get()
        if not cam.running:
            cam.start()
        fp = FingerPointer.get()
        fp.ensure_loaded()
        fp.reset()
        overlay = VirtualMouseOverlay.get()
        overlay.start()
        overlay.wait_ready(timeout=2.0)
        # 预热手部模型与视频跟踪状态
        for _ in range(8):
            frame = cam.read()
            if frame is not None:
                try:
                    fp.track(frame)
                except Exception:
                    logger.debug("finger pointer warmup skipped", exc_info=True)
                    break
            time.sleep(0.03)
        with cls._lock:
            cls._active = True
            cls._smooth_ready = False
            cls._tick_idx = 0
            cls._suspend_until = 0.0
            cls._last_click = 0.0
            cls._last_payload = None
            cls._pinch_screen_locked = False
        cls._start_pointer_thread()
        if not _already_primed:
            # 规避首次打开捏合无效：自动关开一次，等效于用户第二次打开
            cls.stop()
            return cls.start(_already_primed=True)
        return cls.status()

    @classmethod
    def stop(cls) -> dict:
        with cls._lock:
            cls._active = False
            cls._show_keyboard = False
            cls._smooth_ready = False
        cls._pointer_stop.set()
        if cls._pointer_thread and cls._pointer_thread.is_alive():
            cls._pointer_thread.join(timeout=0.5)
        cls._pinch_screen_locked = False
        FingerPointer.get().reset()
        VirtualMouseOverlay.get().stop()
        cls._release_camera_if_idle()
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
    def get_last_payload(cls) -> dict | None:
        return cls._last_payload

    @classmethod
    def _frame_shape(cls, frame) -> tuple[int, int]:
        import cv2

        cfg = get_perception_config()
        h, w = frame.shape[:2]
        if cfg.get("camera_mirror", True):
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
        return h, w

    @classmethod
    def _smooth_pointer(cls, sx: float, sy: float) -> tuple[float, float]:
        cfg = get_perception_config()
        alpha = float(cfg.get("pointer_smooth_alpha") or 0.55)
        if not cls._smooth_ready:
            cls._smooth_x, cls._smooth_y = sx, sy
            cls._smooth_ready = True
            return sx, sy
        cls._smooth_x = cls._smooth_x * (1 - alpha) + sx * alpha
        cls._smooth_y = cls._smooth_y * (1 - alpha) + sy * alpha
        return cls._smooth_x, cls._smooth_y

    @classmethod
    def _process_frame(cls, frame) -> dict:
        h, w = cls._frame_shape(frame)
        track = FingerPointer.get().track(frame)

        payload: dict = {"type": "pointer", "tracking": track.get("visible", False)}
        now = time.time()

        if track.get("hand_box"):
            payload["hand_box"] = track["hand_box"]
        if track.get("index_tip"):
            payload["index_tip"] = track["index_tip"]
        if track.get("pinch"):
            payload["pinch"] = True

        if not track.get("visible"):
            return payload

        click_cooldown = float(get_perception_config().get("virtual_click_cooldown_sec") or 0.35)

        # 捏合点击：在当前光标位置点击，不做坐标映射
        if track.get("pinch"):
            cx, cy = get_cursor_position()
            payload.update(
                {
                    "screen_x": cx,
                    "screen_y": cy,
                    "camera_x": track["camera_x"],
                    "camera_y": track["camera_y"],
                }
            )
            if track.get("pinch_down") and now - cls._last_click > click_cooldown:
                cls._last_click = now
                try:
                    if click_at_cursor():
                        VirtualMouseOverlay.get().update(cx, cy, clicked=True)
                        payload["clicked"] = True
                        FingerPointer.get().consume_pinch()
                    else:
                        payload["error"] = "click_failed:no_injector"
                except Exception as exc:
                    payload["error"] = f"click_failed:{exc}"
            return payload

        mapped = map_camera_to_screen(
            float(track["camera_x"]),
            float(track["camera_y"]),
            frame_shape=(h, w),
        )
        if not mapped:
            payload["map_error"] = "out_of_range"
            return payload

        cls._pinch_screen_locked = False
        sx, sy = cls._smooth_pointer(*mapped)
        try:
            move_pointer(sx, sy)
            VirtualMouseOverlay.get().update(sx, sy, clicked=False)
            cls._last_x, cls._last_y = sx, sy
        except Exception as exc:
            payload["error"] = f"move_failed:{exc}"
            logger.warning("virtual move failed: %s", exc)
            return payload

        payload.update(
            {
                "screen_x": sx,
                "screen_y": sy,
                "camera_x": track["camera_x"],
                "camera_y": track["camera_y"],
            }
        )
        return payload

    @classmethod
    def _tick_sync(cls) -> dict | None:
        if not cls._active:
            return None
        if cls._automation_suspended():
            return {"type": "pointer", "suspended": True}

        cam = CameraService.get()
        if not cam.running:
            try:
                cam.start()
            except Exception as exc:
                return {"type": "pointer", "error": f"camera_start_failed:{exc}"}
        frame = cam.read()
        if frame is None:
            return {"type": "pointer", "error": "camera_frame_empty"}
        return cls._process_frame(frame)

    @classmethod
    async def tick(cls) -> dict | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, cls._tick_sync)

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

    @classmethod
    def preview_mapped_point(cls) -> dict:
        cam = CameraService.get()
        if not cam.running:
            cam.start()
        frame = cam.read()
        if frame is None:
            raise RuntimeError("无法读取摄像头")
        h, w = cls._frame_shape(frame)
        track = FingerPointer.get().track(frame)
        if not track.get("visible"):
            return {"ok": False, "error": "未检测到手指"}
        mapped = map_camera_to_screen(
            float(track["camera_x"]),
            float(track["camera_y"]),
            frame_shape=(h, w),
        )
        if not mapped:
            return {"ok": False, "error": "映射失败"}
        return {
            "ok": True,
            "camera_x": track["camera_x"],
            "camera_y": track["camera_y"],
            "screen_x": mapped[0],
            "screen_y": mapped[1],
        }

    @classmethod
    def air_click_at_fingertip(cls) -> dict:
        from sensehub.execution.tools import gui

        cam = CameraService.get()
        if not cam.running:
            cam.start()
        frame = cam.read()
        if frame is None:
            raise RuntimeError("无法读取摄像头")
        h, w = cls._frame_shape(frame)
        track = FingerPointer.get().track(frame)
        if not track.get("visible"):
            raise RuntimeError("未检测到手指")
        mapped = map_camera_to_screen(
            float(track["camera_x"]),
            float(track["camera_y"]),
            frame_shape=(h, w),
        )
        if not mapped:
            raise RuntimeError("无法映射手指位置")
        sx, sy = mapped
        move_pointer(sx, sy)
        return gui.click({"x": sx, "y": sy, "mapped_screen_x": sx, "mapped_screen_y": sy})
