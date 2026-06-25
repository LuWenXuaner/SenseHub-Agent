"""虚拟屏食指跟踪：摄像头画面线性映射到屏幕（精度要求低，逻辑尽量简单）."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import numpy as np

from sensehub.perception.config import get_perception_config


class FingerPointer:
    """独立于手势流水线的食指跟踪，避免与预览推理抢锁."""

    _instance: "FingerPointer | None" = None

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hands: Any = None
        self._load_error: str | None = None
        self._running_mode_video = False
        self._frame_ts_ms = 0
        self._smooth_x = 0.0
        self._smooth_y = 0.0
        self._has_smooth = False
        self._track_has = False
        self._track_miss = 0
        self._pinch_streak = 0
        self._pinch_frozen = False
        self._was_pinching = False
        self._freeze_x = 0.0
        self._freeze_y = 0.0
        self._click_latched = False
        self._last_track: dict[str, Any] = {"visible": False}

    @classmethod
    def get(cls) -> "FingerPointer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reset(self) -> None:
        with self._lock:
            self._smooth_x = 0.0
            self._smooth_y = 0.0
            self._has_smooth = False
            self._track_has = False
            self._track_miss = 0
            self._pinch_streak = 0
            self._pinch_frozen = False
            self._was_pinching = False
            self._click_latched = False
            self._frame_ts_ms = 0
            self._last_track = {"visible": False}

    def get_last_track(self) -> dict[str, Any]:
        return dict(self._last_track)

    def ensure_loaded(self) -> None:
        with self._lock:
            if self._hands is not None:
                return
            cfg = get_perception_config()
            hand_path = Path(str(cfg.get("hand_landmarker", "")))
            if not hand_path.is_file():
                self._load_error = f"手部模型不存在: {hand_path}"
                raise FileNotFoundError(self._load_error)
            import mediapipe as mp

            BaseOptions = mp.tasks.BaseOptions
            HandLandmarker = mp.tasks.vision.HandLandmarker
            HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
            RunningMode = getattr(mp.tasks.vision, "RunningMode", None)
            video_mode = getattr(RunningMode, "VIDEO", None) if RunningMode else None
            try:
                opts: dict[str, Any] = {
                    "base_options": BaseOptions(model_asset_path=str(hand_path)),
                    "num_hands": 1,
                    "min_hand_detection_confidence": 0.35,
                    "min_hand_presence_confidence": 0.35,
                    "min_tracking_confidence": 0.35,
                }
                if video_mode is not None:
                    opts["running_mode"] = video_mode
                self._hands = HandLandmarker.create_from_options(HandLandmarkerOptions(**opts))
                self._running_mode_video = video_mode is not None
            except TypeError:
                self._hands = HandLandmarker.create_from_options(
                    HandLandmarkerOptions(
                        base_options=BaseOptions(model_asset_path=str(hand_path)),
                        num_hands=1,
                    )
                )
                self._running_mode_video = False
            self._load_error = None

    def _detect(self, frame: np.ndarray):
        mp_image = self._to_mp_image(frame)
        if self._running_mode_video:
            self._frame_ts_ms += 33
            return self._hands.detect_for_video(mp_image, self._frame_ts_ms)
        return self._hands.detect(mp_image)

    @staticmethod
    def _mirror(frame: np.ndarray) -> np.ndarray:
        import cv2

        return cv2.flip(frame, 1)

    def _to_mp_image(self, frame: np.ndarray):
        import cv2
        import mediapipe as mp

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    @staticmethod
    def _hand_bbox(hand, w: int, h: int) -> dict[str, float]:
        xs = [lm.x * w for lm in hand]
        ys = [lm.y * h for lm in hand]
        pad = 8.0
        return {
            "x1": max(0.0, min(xs) - pad),
            "y1": max(0.0, min(ys) - pad),
            "x2": min(float(w), max(xs) + pad),
            "y2": min(float(h), max(ys) + pad),
        }

    def _smooth_tip(self, cx: float, cy: float, alpha: float) -> None:
        if not self._has_smooth:
            self._smooth_x, self._smooth_y = cx, cy
            self._has_smooth = True
        else:
            self._smooth_x = self._smooth_x * (1 - alpha) + cx * alpha
            self._smooth_y = self._smooth_y * (1 - alpha) + cy * alpha

    def consume_pinch(self) -> None:
        """一次捏合只触发一次点击."""
        with self._lock:
            self._click_latched = True
            self._pinch_streak = 0
            self._was_pinching = True

    def track(self, frame_bgr: np.ndarray) -> dict[str, Any]:
        """检测食指尖像素坐标（与预览画面同坐标系）."""
        self.ensure_loaded()
        assert self._hands is not None
        cfg = get_perception_config()
        frame = self._mirror(frame_bgr) if cfg.get("camera_mirror", True) else frame_bgr
        h, w = frame.shape[:2]
        alpha = float(cfg.get("pointer_track_alpha") or 0.65)
        pinch_thresh = float(cfg.get("virtual_pinch_threshold") or 0.072)
        pinch_confirm = max(1, int(cfg.get("virtual_pinch_confirm_frames") or 1))
        hold_frames = int(cfg.get("virtual_track_hold_frames") or 3)

        with self._lock:
            result = self._detect(frame)

            if not result.hand_landmarks:
                self._track_miss += 1
                if self._track_has and self._track_miss <= hold_frames:
                    payload = {
                        "visible": True,
                        "camera_x": self._smooth_x,
                        "camera_y": self._smooth_y,
                        "pinch": False,
                        "pinch_down": False,
                        "held": True,
                    }
                    self._last_track = payload
                    return dict(payload)

                self._pinch_streak = 0
                self._pinch_frozen = False
                self._was_pinching = False
                self._click_latched = False
                self._track_has = False
                payload = {
                    "visible": False,
                    "camera_x": 0.0,
                    "camera_y": 0.0,
                    "pinch": False,
                    "pinch_down": False,
                }
                self._last_track = payload
                return dict(payload)

            self._track_miss = 0
            self._track_has = True
            hand = result.hand_landmarks[0]
            tip, thumb = hand[8], hand[4]
            cx = float(tip.x * w)
            cy = float(tip.y * h)

            pinch_dist = float(((thumb.x - tip.x) ** 2 + (thumb.y - tip.y) ** 2) ** 0.5)
            pinch = pinch_dist < pinch_thresh
            pinch_down = False

            if pinch:
                if not self._pinch_frozen:
                    self._smooth_tip(cx, cy, alpha)
                    self._freeze_x = self._smooth_x
                    self._freeze_y = self._smooth_y
                    self._pinch_frozen = True
                self._pinch_streak += 1
                rising_edge = not self._was_pinching
                if rising_edge and not self._click_latched:
                    pinch_down = True
                elif self._pinch_streak >= pinch_confirm and not self._click_latched:
                    pinch_down = True
                self._was_pinching = True
                out_x, out_y = self._freeze_x, self._freeze_y
            else:
                self._pinch_streak = 0
                self._pinch_frozen = False
                self._was_pinching = False
                self._click_latched = False
                self._smooth_tip(cx, cy, alpha)
                out_x, out_y = self._smooth_x, self._smooth_y

            payload = {
                "visible": True,
                "camera_x": out_x,
                "camera_y": out_y,
                "pinch": pinch,
                "pinch_down": pinch_down,
                "hand_box": self._hand_bbox(hand, w, h),
                "index_tip": {"x": out_x, "y": out_y},
                "frame_width": w,
                "frame_height": h,
            }
            self._last_track = dict(payload)
            return dict(payload)
