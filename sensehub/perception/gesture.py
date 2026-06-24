"""YOLO Pose 手势检测（举手等，Phase 3）."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import numpy as np

from sensehub.perception.device import inference_device
from sensehub.settings import get_settings

# COCO pose: 左腕 9, 右腕 10, 左肩 5, 右肩 6
_WRIST = (9, 10)
_SHOULDER = (5, 6)


class GestureDetector:
    _instance: GestureDetector | None = None

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model: Any = None
        self._weights = ""
        self._device = "cpu"

    @classmethod
    def get(cls) -> GestureDetector:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _resolve_weights(self) -> Path:
        settings = get_settings()
        w = settings.paths.get("models", {}).get("yolo_pose_weights", "")
        if not w:
            w = str(Path(settings.models_root) / "yolov8n-pose.pt")
        return Path(w)

    def ensure_loaded(self) -> None:
        with self._lock:
            if self._model is not None:
                return
            path = self._resolve_weights()
            if not path.exists():
                raise FileNotFoundError(f"Pose 权重不存在: {path}")
            from ultralytics import YOLO

            device = inference_device()
            self._model = YOLO(str(path))
            self._model.to(device)
            self._device = device
            self._weights = str(path)

    def detect(self, frame: np.ndarray) -> list[dict[str, Any]]:
        """返回检测到的手势列表."""
        self.ensure_loaded()
        assert self._model is not None
        results = self._model.predict(frame, verbose=False, device=self._device, imgsz=640)
        gestures: list[dict[str, Any]] = []
        for result in results:
            if result.keypoints is None:
                continue
            kpts = result.keypoints.xy.cpu().numpy()
            conf = result.keypoints.conf
            if conf is None:
                continue
            conf_np = conf.cpu().numpy()
            for person_idx, person_kpts in enumerate(kpts):
                if person_kpts.shape[0] < 11:
                    continue
                for wrist_i, shoulder_i in zip(_WRIST, _SHOULDER):
                    wc = float(conf_np[person_idx][wrist_i]) if person_idx < len(conf_np) else 0.5
                    sc = float(conf_np[person_idx][shoulder_i]) if person_idx < len(conf_np) else 0.5
                    if wc < 0.4 or sc < 0.4:
                        continue
                    wx, wy = person_kpts[wrist_i]
                    sx, sy = person_kpts[shoulder_i]
                    if wy < sy - 20:  # 手腕高于肩 → 举手
                        gestures.append(
                            {
                                "gesture": "hand_raised",
                                "confidence": (wc + sc) / 2,
                                "wrist": {"x": float(wx), "y": float(wy)},
                            }
                        )
        return gestures

    def fingertip_for_virtual_screen(self, frame: np.ndarray) -> tuple[float, float] | None:
        """Phase 4：返回食指近似点（用腕部作为简化指针）."""
        self.ensure_loaded()
        assert self._model is not None
        results = self._model.predict(frame, verbose=False, device=self._device, imgsz=640)
        for result in results:
            if result.keypoints is None:
                continue
            kpts = result.keypoints.xy.cpu().numpy()
            if len(kpts) == 0 or kpts[0].shape[0] < 11:
                continue
            # 右腕作为指向点
            wx, wy = kpts[0][10]
            return float(wx), float(wy)
        return None
