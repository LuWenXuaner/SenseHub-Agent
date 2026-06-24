"""OpenCV 摄像头采集."""

from __future__ import annotations

import threading
import time
from typing import Any

import numpy as np

from sensehub.settings import get_settings


class CameraService:
    """单例摄像头服务，默认关闭."""

    _instance: CameraService | None = None

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cap: Any = None
        self._running = False
        self._index = 0
        self._last_error: str | None = None
        self._last_frame: np.ndarray | None = None
        self._frame_time = 0.0

    @classmethod
    def get(cls) -> CameraService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def camera_index(self) -> int:
        settings = get_settings()
        devices = settings.paths.get("devices", {})
        if "camera_index" in devices:
            return int(devices["camera_index"])
        return int(settings.camera_index)

    def start(self) -> None:
        import cv2

        with self._lock:
            if self._running:
                return
            self._index = self.camera_index()
            self._cap = cv2.VideoCapture(self._index)
            if not self._cap.isOpened():
                self._last_error = f"无法打开摄像头 index={self._index}"
                self._cap = None
                raise RuntimeError(self._last_error)
            self._running = True
            self._last_error = None

    def stop(self) -> None:
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            self._running = False
            self._last_frame = None

    def read(self) -> np.ndarray | None:
        import cv2

        with self._lock:
            if not self._running or self._cap is None:
                return None
            ok, frame = self._cap.read()
            if not ok or frame is None:
                self._last_error = "读取摄像头帧失败"
                return None
            self._last_frame = frame
            self._frame_time = time.time()
            self._last_error = None
            return frame

    def encode_jpeg(self, frame: np.ndarray, quality: int = 72) -> bytes:
        import cv2

        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            raise RuntimeError("JPEG 编码失败")
        return buf.tobytes()
