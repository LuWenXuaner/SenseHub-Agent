"""YOLO 人员检测."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import numpy as np

from sensehub.models.perception_schemas import DetectionBox
from sensehub.perception.device import inference_device
from sensehub.settings import get_settings

_PERSON_CLASS_ID = 0


class YoloDetector:
    _instance: YoloDetector | None = None

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model: Any = None
        self._weights_path = ""
        self._device = "cpu"
        self._load_error: str | None = None

    @classmethod
    def get(cls) -> YoloDetector:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def ready(self) -> bool:
        return self._model is not None

    @property
    def weights_path(self) -> str:
        return self._weights_path

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def device(self) -> str:
        return self._device

    def _resolve_weights(self) -> Path:
        settings = get_settings()
        weights = settings.paths.get("models", {}).get("yolo_weights", "")
        if not weights:
            weights = str(Path(settings.models_root) / "yolov8n.pt")
        return Path(weights)

    def ensure_loaded(self) -> None:
        with self._lock:
            if self._model is not None:
                return
            path = self._resolve_weights()
            if not path.exists():
                self._load_error = f"YOLO 权重不存在: {path}"
                raise FileNotFoundError(self._load_error)
            try:
                from ultralytics import YOLO

                device = inference_device()
                self._model = YOLO(str(path))
                self._model.to(device)
                self._weights_path = str(path)
                self._device = device
                self._load_error = None
            except Exception as exc:
                self._load_error = str(exc)
                raise

    def detect_persons(
        self,
        frame: np.ndarray,
        *,
        confidence_min: float = 0.5,
    ) -> list[DetectionBox]:
        self.ensure_loaded()
        assert self._model is not None
        results = self._model.predict(
            frame,
            verbose=False,
            device=self._device,
            classes=[_PERSON_CLASS_ID],
            imgsz=640,
        )
        boxes: list[DetectionBox] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf < confidence_min:
                    continue
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
                boxes.append(
                    DetectionBox(
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                        confidence=conf,
                        label="person",
                    )
                )
        return boxes
