"""MediaPipe 手/脸动作：挥手、点头、摇头 + 食指尖指向."""

from __future__ import annotations

import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

from sensehub.perception.config import get_perception_config

_GESTURE_LABELS = {
    "wave": "检测到挥手",
    "nod": "检测到点头",
    "shake": "检测到摇头",
    "hand_raised": "检测到举手",
    "none": "未检测到手势",
}


def _count_zero_crossings(values: list[float]) -> int:
    changes = 0
    for i in range(2, len(values)):
        prev = values[i - 1] - values[i - 2]
        curr = values[i] - values[i - 1]
        if prev * curr < 0:
            changes += 1
    return changes


class MediaPipeGestureRecognizer:
    _instance: MediaPipeGestureRecognizer | None = None

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._detect_lock = threading.Lock()
        self._hands: Any = None
        self._face: Any = None
        self._load_error: str | None = None
        self.index_history: deque = deque(maxlen=24)
        self.head_history: deque = deque(maxlen=24)
        self.nod_count = 0
        self.shake_count = 0
        self.last_nod_time = 0.0
        self.last_shake_time = 0.0
        self._pending: dict[str, int] = {}
        self._confirmed_type = "none"
        self._confirmed_confidence = 0.0
        self._confirmed_at = 0.0
        self._raw_type = "none"
        self._raw_confidence = 0.0
        self._track_cam_x = 0.0
        self._track_cam_y = 0.0
        self._track_has = False
        self._track_miss = 0
        self._last_pinch = False
        self._pinch_streak = 0
        self._preferred_handedness: str | None = None
        self._last_hand_box: dict[str, float] | None = None
        self._last_index_tip: dict[str, float] | None = None
        self._last_virtual_track: dict[str, Any] = {
            "visible": False,
            "camera_x": 0.0,
            "camera_y": 0.0,
            "pinch": False,
            "pinch_down": False,
            "held": False,
        }

    @classmethod
    def get(cls) -> MediaPipeGestureRecognizer:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def ready(self) -> bool:
        return self._hands is not None and self._face is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def _cfg(self) -> dict[str, Any]:
        return get_perception_config()

    def ensure_loaded(self) -> None:
        with self._lock:
            if self._hands is not None:
                return
            cfg = self._cfg()
            hand_path = Path(str(cfg.get("hand_landmarker", "")))
            face_path = Path(str(cfg.get("face_landmarker", "")))
            if not hand_path.is_file():
                self._load_error = f"手部模型不存在: {hand_path}"
                raise FileNotFoundError(self._load_error)
            if not face_path.is_file():
                self._load_error = f"面部模型不存在: {face_path}"
                raise FileNotFoundError(self._load_error)
            try:
                import mediapipe as mp

                BaseOptions = mp.tasks.BaseOptions
                HandLandmarker = mp.tasks.vision.HandLandmarker
                HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
                FaceLandmarker = mp.tasks.vision.FaceLandmarker
                FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions

                self._hands = HandLandmarker.create_from_options(
                    HandLandmarkerOptions(
                        base_options=BaseOptions(model_asset_path=str(hand_path)),
                        num_hands=2,
                        min_hand_detection_confidence=0.55,
                        min_hand_presence_confidence=0.55,
                        min_tracking_confidence=0.55,
                    )
                )
                self._face = FaceLandmarker.create_from_options(
                    FaceLandmarkerOptions(
                        base_options=BaseOptions(model_asset_path=str(face_path)),
                        num_faces=1,
                        min_face_detection_confidence=0.55,
                        min_face_presence_confidence=0.55,
                        min_tracking_confidence=0.55,
                    )
                )
                self._load_error = None
            except TypeError:
                # 旧版 mediapipe 无 min_* 参数
                import mediapipe as mp

                BaseOptions = mp.tasks.BaseOptions
                HandLandmarker = mp.tasks.vision.HandLandmarker
                HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
                FaceLandmarker = mp.tasks.vision.FaceLandmarker
                FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
                self._hands = HandLandmarker.create_from_options(
                    HandLandmarkerOptions(
                        base_options=BaseOptions(model_asset_path=str(hand_path)),
                        num_hands=2,
                    )
                )
                self._face = FaceLandmarker.create_from_options(
                    FaceLandmarkerOptions(
                        base_options=BaseOptions(model_asset_path=str(face_path)),
                        num_faces=1,
                    )
                )
                self._load_error = None
            except Exception as exc:
                self._load_error = str(exc)
                raise

    def _to_mp_image(self, frame: np.ndarray):
        import cv2
        import mediapipe as mp

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    def _detect_raw(self, frame: np.ndarray) -> tuple[str, float, dict[str, Any]]:
        cfg = self._cfg()
        hand_count = 0
        extras: dict[str, Any] = {}

        self.ensure_loaded()
        assert self._hands is not None and self._face is not None

        mp_image = self._to_mp_image(frame)
        with self._detect_lock:
            hand_result = self._hands.detect(mp_image)
            face_result = self._face.detect(mp_image)
        h, w = frame.shape[:2]

        # --- 手：挥手 / 举手 ---
        if hand_result.hand_landmarks:
            hand_count = len(hand_result.hand_landmarks)
            extras["hand_count"] = hand_count
            best_wave_span = 0.0
            wave_conf = 0.0
            raise_conf = 0.0
            raise_delta = float(cfg.get("hand_raise_min_delta", 0.09))

            for hand_landmarks in hand_result.hand_landmarks:
                wrist = hand_landmarks[0]
                index_tip = hand_landmarks[8]
                index_pip = hand_landmarks[6]
                middle_tip = hand_landmarks[12]

                self.index_history.append(
                    {"x": index_tip.x, "y": index_tip.y, "wrist_y": wrist.y, "time": time.time()}
                )

                index_above = index_tip.y < wrist.y - raise_delta
                finger_extended = index_tip.y < index_pip.y - 0.03
                palm_high = wrist.y < 0.72
                if index_above and finger_extended and palm_high:
                    delta = wrist.y - index_tip.y
                    raise_conf = max(raise_conf, min(0.95, 0.55 + delta * 2.5))
                    extras["index_tip"] = {"x": index_tip.x * w, "y": index_tip.y * h}

                if middle_tip.y < wrist.y - 0.04 and wrist.y < 0.7:
                    if len(self.index_history) >= 12:
                        recent = list(self.index_history)[-12:]
                        xs = [p["x"] for p in recent]
                        span = max(xs) - min(xs)
                        rev = _count_zero_crossings(xs)
                        if span > best_wave_span:
                            best_wave_span = span
                        min_span = float(cfg.get("wave_min_span", 0.18))
                        min_rev = int(cfg.get("wave_min_reversals", 4))
                        if span >= min_span and rev >= min_rev:
                            wave_conf = max(wave_conf, min(0.92, span * 2.8 + rev * 0.06))

            if wave_conf >= float(cfg.get("gesture_min_confidence", 0.62)):
                return "wave", wave_conf, extras
            if raise_conf >= float(cfg.get("gesture_min_confidence", 0.62)):
                return "hand_raised", raise_conf, extras

        # --- 头：点头 / 摇头 ---
        if face_result.face_landmarks:
            lm = face_result.face_landmarks[0]
            nose = lm[1]
            chin = lm[152]
            self.head_history.append(
                {
                    "nose_y": nose.y,
                    "nose_x": nose.x,
                    "rel_y": nose.y - chin.y,
                    "time": time.time(),
                }
            )
            if len(self.head_history) >= 16:
                recent = list(self.head_history)[-16:]
                rel_y = [p["rel_y"] for p in recent]
                nose_x = [p["nose_x"] for p in recent]
                y_range = max(rel_y) - min(rel_y)
                x_range = max(nose_x) - min(nose_x)
                y_rev = _count_zero_crossings(rel_y)
                x_rev = _count_zero_crossings(nose_x)

                nod_lo = float(cfg.get("nod_min_y_range", 0.034))
                nod_hi = float(cfg.get("nod_max_y_range", 0.11))
                nod_rev = int(cfg.get("nod_min_reversals", 4))
                shake_lo = float(cfg.get("shake_min_x_range", 0.048))
                shake_hi = float(cfg.get("shake_max_x_range", 0.12))
                shake_rev = int(cfg.get("shake_min_reversals", 4))
                min_conf = float(cfg.get("gesture_min_confidence", 0.62))

                nod_score = 0.0
                if nod_lo < y_range < nod_hi and y_rev >= nod_rev:
                    nod_score = min(0.92, y_rev / 6 + y_range * 4)
                shake_score = 0.0
                if shake_lo < x_range < shake_hi and x_rev >= shake_rev:
                    shake_score = min(0.92, x_rev / 6 + x_range * 3)

                if nod_score >= min_conf and nod_score >= shake_score:
                    now = time.time()
                    if now - self.last_nod_time > 1.2:
                        self.nod_count += 1
                        self.last_nod_time = now
                    return "nod", nod_score, extras
                if shake_score >= min_conf:
                    now = time.time()
                    if now - self.last_shake_time > 1.2:
                        self.shake_count += 1
                        self.last_shake_time = now
                    return "shake", shake_score, extras

        return "none", 0.0, extras

    def _confirm(self, raw_type: str, raw_conf: float) -> tuple[str, float]:
        cfg = self._cfg()
        need = int(cfg.get("gesture_confirm_frames", 3))
        hold = float(cfg.get("gesture_hold_sec", 1.2))
        min_conf = float(cfg.get("gesture_min_confidence", 0.62))
        now = time.time()

        self._raw_type = raw_type
        self._raw_confidence = raw_conf

        if raw_type == "none" or raw_conf < min_conf:
            for k in list(self._pending):
                self._pending[k] = max(0, self._pending[k] - 1)
                if self._pending[k] <= 0:
                    del self._pending[k]
        else:
            for k in list(self._pending):
                if k != raw_type:
                    del self._pending[k]
            self._pending[raw_type] = self._pending.get(raw_type, 0) + 1
            if self._pending[raw_type] >= need:
                self._confirmed_type = raw_type
                self._confirmed_confidence = raw_conf
                self._confirmed_at = now

        if self._confirmed_type != "none" and now - self._confirmed_at > hold:
            self._confirmed_type = "none"
            self._confirmed_confidence = 0.0

        if self._confirmed_type != "none":
            return self._confirmed_type, self._confirmed_confidence
        return "none", 0.0

    def recognize_gesture(self, frame: np.ndarray) -> dict[str, Any]:
        raw_type, raw_conf, extras = self._detect_raw(frame)
        gtype, conf = self._confirm(raw_type, raw_conf)
        hand_count = int(extras.get("hand_count") or 0)
        out: dict[str, Any] = {
            "type": gtype,
            "confidence": conf,
            "description": _GESTURE_LABELS.get(gtype, gtype),
            "hand_count": hand_count,
            "raw_type": self._raw_type,
            "raw_confidence": round(self._raw_confidence, 3),
        }
        if gtype == "nod":
            out["nod_count"] = self.nod_count
        if gtype == "shake":
            out["shake_count"] = self.shake_count
        if self._raw_type not in ("none", gtype) and self._raw_confidence >= float(
            self._cfg().get("gesture_min_confidence", 0.62)
        ):
            out["hint"] = f"疑似{_GESTURE_LABELS.get(self._raw_type, self._raw_type)}"
        return out

    def reset_virtual_track(self) -> None:
        self._track_cam_x = 0.0
        self._track_cam_y = 0.0
        self._track_has = False
        self._track_miss = 0
        self._last_pinch = False
        self._pinch_streak = 0
        self._preferred_handedness = None
        self._last_hand_box = None
        self._last_index_tip = None
        self._last_virtual_track = {
            "visible": False,
            "camera_x": 0.0,
            "camera_y": 0.0,
            "pinch": False,
            "pinch_down": False,
            "held": False,
        }

    def get_last_virtual_track(self) -> dict[str, Any]:
        return dict(self._last_virtual_track)

    @staticmethod
    def _index_extension_score(hand) -> float:
        tip, pip, mcp = hand[8], hand[6], hand[5]
        ext = float(((tip.x - pip.x) ** 2 + (tip.y - pip.y) ** 2) ** 0.5)
        ref = float(((pip.x - mcp.x) ** 2 + (pip.y - mcp.y) ** 2) ** 0.5) + 1e-6
        return ext / ref

    @staticmethod
    def _hand_bbox(hand, w: int, h: int) -> dict[str, float]:
        xs = [lm.x * w for lm in hand]
        ys = [lm.y * h for lm in hand]
        pad = 10.0
        return {
            "x1": max(0.0, min(xs) - pad),
            "y1": max(0.0, min(ys) - pad),
            "x2": min(float(w), max(xs) + pad),
            "y2": min(float(h), max(ys) + pad),
        }

    def _finalize_virtual_track(self, payload: dict[str, Any], hand=None, w: int = 0, h: int = 0) -> dict[str, Any]:
        if hand is not None and w > 0 and h > 0:
            payload["hand_box"] = self._hand_bbox(hand, w, h)
            tip = hand[8]
            payload["index_tip"] = {"x": float(tip.x * w), "y": float(tip.y * h)}
            self._last_hand_box = dict(payload["hand_box"])
            self._last_index_tip = dict(payload["index_tip"])
        elif payload.get("visible") and self._last_hand_box and self._last_index_tip:
            payload["hand_box"] = dict(self._last_hand_box)
            payload["index_tip"] = dict(self._last_index_tip)
        self._last_virtual_track = dict(payload)
        return payload

    def track_virtual_pointer(self, frame: np.ndarray) -> dict[str, Any]:
        """全画面检测食指并连续跟踪；捏合触发点击."""
        self.ensure_loaded()
        assert self._hands is not None
        cfg = self._cfg()
        h, w = frame.shape[:2]
        hold_frames = int(cfg.get("virtual_track_hold_frames") or 3)
        alpha = float(cfg.get("pointer_track_alpha") or 0.72)
        pinch_thresh = float(cfg.get("virtual_pinch_threshold") or 0.058)
        pinch_confirm = int(cfg.get("virtual_pinch_confirm_frames") or 2)

        with self._detect_lock:
            result = self._hands.detect(self._to_mp_image(frame))

        if not result.hand_landmarks:
            self._track_miss += 1
            self._pinch_streak = 0
            self._last_pinch = False
            if self._track_has and self._track_miss <= hold_frames:
                return self._finalize_virtual_track(
                    {
                        "visible": True,
                        "camera_x": self._track_cam_x,
                        "camera_y": self._track_cam_y,
                        "pinch": False,
                        "pinch_down": False,
                        "held": True,
                    }
                )
            return self._finalize_virtual_track(
                {
                    "visible": False,
                    "camera_x": 0.0,
                    "camera_y": 0.0,
                    "pinch": False,
                    "pinch_down": False,
                    "held": False,
                }
            )

        best = None
        best_score = -1e9
        best_label: str | None = None
        for idx, hand in enumerate(result.hand_landmarks):
            tip, wrist, index_pip = hand[8], hand[0], hand[6]
            # 参考 multimodal：优先用食指尖；伸展度 + 指尖高于手腕加分
            ext = self._index_extension_score(hand)
            score = ext + max(0.0, (wrist.y - tip.y) * 0.8) + max(0.0, (index_pip.y - tip.y) * 0.4)
            label = None
            if result.handedness and idx < len(result.handedness):
                cats = result.handedness[idx]
                if cats.classification:
                    label = str(cats.classification[0].category_name or "")
            if self._preferred_handedness and label and label != self._preferred_handedness:
                continue
            if score > best_score:
                best_score = score
                best = hand
                best_label = label

        if best is None and self._preferred_handedness:
            for hand in result.hand_landmarks:
                ext = self._index_extension_score(hand)
                tip, wrist, index_pip = hand[8], hand[0], hand[6]
                score = ext + max(0.0, (wrist.y - tip.y) * 0.8)
                if score > best_score:
                    best_score = score
                    best = hand
                    best_label = None

        # 任意检测到的手都接受（与 multimodal 一致，避免指向镜头时过滤过严）
        if best is None and result.hand_landmarks:
            best = result.hand_landmarks[0]
            best_score = 0.5

        if best is None or best_score < 0.08:
            self._track_miss += 1
            self._pinch_streak = 0
            self._last_pinch = False
            if self._track_has and self._track_miss <= hold_frames:
                return self._finalize_virtual_track(
                    {
                        "visible": True,
                        "camera_x": self._track_cam_x,
                        "camera_y": self._track_cam_y,
                        "pinch": False,
                        "pinch_down": False,
                        "held": True,
                    }
                )
            return self._finalize_virtual_track(
                {
                    "visible": False,
                    "camera_x": 0.0,
                    "camera_y": 0.0,
                    "pinch": False,
                    "pinch_down": False,
                    "held": False,
                }
            )

        if best_label and not self._preferred_handedness:
            self._preferred_handedness = best_label

        tip = best[8]
        thumb = best[4]
        cx = float(tip.x * w)
        cy = float(tip.y * h)
        if not self._track_has:
            self._track_cam_x, self._track_cam_y = cx, cy
            self._track_has = True
        else:
            self._track_cam_x = self._track_cam_x * (1 - alpha) + cx * alpha
            self._track_cam_y = self._track_cam_y * (1 - alpha) + cy * alpha
        self._track_miss = 0

        pinch_dist = float(((thumb.x - tip.x) ** 2 + (thumb.y - tip.y) ** 2) ** 0.5)
        pinch = pinch_dist < pinch_thresh
        self._pinch_streak = self._pinch_streak + 1 if pinch else 0
        pinch_down = self._pinch_streak == pinch_confirm
        self._last_pinch = pinch

        return self._finalize_virtual_track(
            {
                "visible": True,
                "camera_x": self._track_cam_x,
                "camera_y": self._track_cam_y,
                "pinch": pinch,
                "pinch_down": pinch_down,
                "held": False,
            },
            hand=best,
            w=w,
            h=h,
        )

    def index_fingertip_pixels(
        self,
        frame: np.ndarray,
        *,
        person_box: tuple[float, float, float, float] | None = None,
    ) -> tuple[float, float] | None:
        self.ensure_loaded()
        assert self._hands is not None
        roi = frame
        ox, oy = 0.0, 0.0
        if person_box:
            x1, y1, x2, y2 = person_box
            fh, fw = frame.shape[:2]
            x1i = max(0, int(x1))
            y1i = max(0, int(y1))
            x2i = min(fw, int(x2))
            y2i = min(fh, int(y2))
            if x2i - x1i > 20 and y2i - y1i > 20:
                roi = frame[y1i:y2i, x1i:x2i]
                ox, oy = float(x1i), float(y1i)
        with self._detect_lock:
            result = self._hands.detect(self._to_mp_image(roi))
        if not result.hand_landmarks:
            return None
        hand = result.hand_landmarks[0]
        tip = hand[8]
        wrist = hand[0]
        if tip.y > wrist.y - 0.02:
            return None
        rh, rw = roi.shape[:2]
        return tip.x * rw + ox, tip.y * rh + oy
