"""摄像头帧广播：全局单循环，避免多 WebSocket 重复推理导致内存/GPU 暴涨."""

from __future__ import annotations

import asyncio
import base64
import logging
import time

from sensehub.licensing.tier import feature_enabled
from sensehub.perception.camera import CameraService
from sensehub.perception.config import get_perception_config
from sensehub.perception.detector import YoloDetector
from sensehub.perception.mediapipe_gesture import MediaPipeGestureRecognizer
from sensehub.perception.pipeline import PerceptionPipeline

logger = logging.getLogger(__name__)


class CameraStreamBroadcaster:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._clients: set = set()
        self._lock = asyncio.Lock()
        self._pipeline = PerceptionPipeline()

    def attach(self, ws, manager) -> None:
        self._clients.add(ws)
        manager.active.append(ws)

    def detach(self, ws, manager) -> None:
        self._clients.discard(ws)
        if ws in manager.active:
            manager.active.remove(ws)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def ensure_running(self, manager) -> None:
        async with self._lock:
            if self._task and not self._task.done():
                return
            self._task = asyncio.create_task(self._run(manager))

    async def stop_if_idle(self) -> None:
        async with self._lock:
            if self._clients:
                return
            await self._cancel_task_locked()

    async def shutdown(self) -> None:
        """强制停止广播（用户主动关摄像头时，不等待 WS 断开）."""
        async with self._lock:
            self._clients.clear()
            await self._cancel_task_locked()

    async def _cancel_task_locked(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        try:
            from sensehub.perception.virtual_session import VirtualScreenSession

            if not VirtualScreenSession.is_active():
                CameraService.get().stop()
        except Exception:
            pass

    async def _run(self, manager) -> None:
        cam = CameraService.get()
        cfg = get_perception_config()
        try:
            if not cam.running:
                cam.start()
            YoloDetector.get().ensure_loaded()
            if feature_enabled("gesture_rules"):
                backend = str(cfg.get("gesture_backend") or "mediapipe")
                if backend == "mediapipe":
                    MediaPipeGestureRecognizer.get().ensure_loaded()
                else:
                    from sensehub.perception.gesture import GestureDetector

                    GestureDetector.get().ensure_loaded()
        except Exception as exc:
            await manager.broadcast({"type": "error", "message": str(exc)})
            return

        loop = asyncio.get_running_loop()
        last_tick = time.perf_counter()
        frames = 0
        preview_ms = float(cfg.get("preview_interval_ms") or 100) / 1000.0
        jpeg_q = int(cfg.get("jpeg_quality") or 55)

        try:
            while self._clients:
                frame = await loop.run_in_executor(None, cam.read)
                if frame is None:
                    await asyncio.sleep(0.05)
                    continue

                perception = await loop.run_in_executor(
                    None, lambda f=frame: self._pipeline.process(f)
                )

                jpeg = await loop.run_in_executor(
                    None, lambda f=frame: cam.encode_jpeg(f, quality=jpeg_q)
                )
                b64 = base64.b64encode(jpeg).decode("ascii")
                frames += 1
                now = time.perf_counter()
                fps = frames / (now - last_tick) if now > last_tick else 0
                if now - last_tick >= 2.0:
                    last_tick = now
                    frames = 0

                if not self._clients:
                    break

                await manager.broadcast(
                    {
                        "type": "frame",
                        "image": b64,
                        "fps": round(fps, 1),
                        "detections": perception.get("detections") or [],
                        "gestures": [perception.get("gesture")] if perception.get("gesture") else [],
                        "gesture": perception.get("gesture"),
                        "person_count": perception.get("person_count", 0),
                        "intent": perception.get("intent"),
                        "hands": perception.get("hands") or [],
                    }
                )
                await asyncio.sleep(preview_ms)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("camera broadcaster failed")
            await manager.broadcast({"type": "error", "message": str(exc)})
        finally:
            self._task = None
        try:
            from sensehub.perception.virtual_session import VirtualScreenSession

            VirtualScreenSession._release_camera_if_idle()
        except Exception:
            pass


camera_broadcaster = CameraStreamBroadcaster()
