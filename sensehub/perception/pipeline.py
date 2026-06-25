"""摄像头感知流水线：抽帧 YOLO + MediaPipe."""

from __future__ import annotations

from typing import Any

import numpy as np

from sensehub.models.perception_schemas import DetectionBox
from sensehub.perception.config import get_perception_config
from sensehub.perception.context import PerceptionContext
from sensehub.perception.detector import YoloDetector
from sensehub.perception.finger_pointer import FingerPointer
from sensehub.perception.mediapipe_gesture import MediaPipeGestureRecognizer
from sensehub.rules import engine as rule_engine


def _mirror_frame(frame: np.ndarray) -> np.ndarray:
    import cv2

    return cv2.flip(frame, 1)


def _crop_person(frame: np.ndarray, box: DetectionBox) -> np.ndarray | None:
    h, w = frame.shape[:2]
    x1 = max(0, int(box.x1))
    y1 = max(0, int(box.y1))
    x2 = min(w, int(box.x2))
    y2 = min(h, int(box.y2))
    if x2 - x1 < 20 or y2 - y1 < 20:
        return None
    return frame[y1:y2, x1:x2]


def _analyze_intent(person_count: int, gesture: dict[str, Any]) -> dict[str, Any]:
    gtype = str(gesture.get("type") or "none")
    if gtype == "wave":
        return {"primary": "user_greeting", "description": "用户在挥手打招呼", "confidence": gesture.get("confidence", 0)}
    if gtype == "nod":
        return {"primary": "user_agreeing", "description": "用户在点头", "confidence": gesture.get("confidence", 0)}
    if gtype == "shake":
        return {"primary": "user_disagreeing", "description": "用户在摇头", "confidence": gesture.get("confidence", 0)}
    if person_count > 0:
        return {"primary": "user_present", "description": f"检测到 {person_count} 人", "confidence": 0.8}
    return {"primary": "no_activity", "description": "未检测到用户活动", "confidence": 0.7}


class PerceptionPipeline:
    def __init__(self) -> None:
        self.frame_idx = 0
        self.last_boxes: list[DetectionBox] = []
        self.last_gesture: dict[str, Any] = {
            "type": "none",
            "confidence": 0.0,
            "description": "未检测到手势",
        }
        self.last_person_count = 0
        self.last_largest_box: DetectionBox | None = None

    def process(self, frame: np.ndarray) -> dict[str, Any]:
        cfg = get_perception_config()
        if cfg.get("camera_mirror"):
            frame = _mirror_frame(frame)

        self.frame_idx += 1
        detect_every = int(cfg.get("detect_every_n_frames") or 5)
        gesture_every = int(cfg.get("gesture_every_n_frames") or 5)
        gesture_only_person = bool(cfg.get("gesture_only_if_person", True))
        backend = str(cfg.get("gesture_backend") or "mediapipe").lower()

        if self.frame_idx % detect_every == 0:
            boxes = YoloDetector.get().detect_persons(frame, confidence_min=0.5)
            self.last_boxes = boxes
            self.last_person_count = len(boxes)
            self.last_largest_box = max(boxes, key=lambda b: (b.x2 - b.x1) * (b.y2 - b.y1)) if boxes else None
            if boxes:
                best = max(boxes, key=lambda b: b.confidence)
                rule_engine.handle_vision_event(
                    "person_detected",
                    confidence=best.confidence,
                    payload={"count": len(boxes)},
                )

        run_gesture = self.frame_idx % gesture_every == 0
        virtual_active = False
        try:
            from sensehub.perception.virtual_session import VirtualScreenSession

            virtual_active = VirtualScreenSession.is_active()
        except Exception:
            pass

        if virtual_active:
            track = FingerPointer.get().get_last_track()
            hands = []
            if track.get("hand_box"):
                hands.append(
                    {
                        "hand_box": track["hand_box"],
                        "index_tip": track.get("index_tip"),
                        "tracking": bool(track.get("visible")),
                        "pinch": bool(track.get("pinch")),
                    }
                )
            payload_hands = hands
        else:
            payload_hands = []

        if run_gesture and (not gesture_only_person or self.last_person_count > 0) and not virtual_active:
            try:
                if backend == "mediapipe":
                    mp = MediaPipeGestureRecognizer.get()
                    mp.ensure_loaded()
                    roi = frame
                    if self.last_largest_box:
                        cropped = _crop_person(frame, self.last_largest_box)
                        if cropped is not None:
                            roi = cropped
                    gesture = mp.recognize_gesture(roi)
                else:
                    from sensehub.perception.gesture import GestureDetector

                    gdet = GestureDetector.get()
                    raw = gdet.detect(frame)
                    if raw:
                        gesture = {
                            "type": "hand_raised",
                            "confidence": raw[0].get("confidence", 0.5),
                            "description": "检测到举手",
                        }
                    else:
                        gesture = {"type": "none", "confidence": 0.0, "description": "未检测到手势"}
                if gesture.get("type") != "none":
                    self.last_gesture = gesture
                    rule_engine.handle_gesture_event(
                        str(gesture["type"]),
                        confidence=float(gesture.get("confidence") or 0),
                        payload=gesture,
                    )
                else:
                    self.last_gesture = gesture
            except Exception:
                pass

        intent = _analyze_intent(self.last_person_count, self.last_gesture)
        detections = [b.model_dump() for b in self.last_boxes]
        payload = {
            "person_count": self.last_person_count,
            "detections": detections,
            "gesture": self.last_gesture,
            "intent": intent,
            "hands": payload_hands,
        }
        PerceptionContext.get().update(payload)
        return payload
