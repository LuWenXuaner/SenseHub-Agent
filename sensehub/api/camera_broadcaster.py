"""摄像头帧广播：全局单循环，避免多 WebSocket 重复推理导致内存/GPU 暴涨."""

from __future__ import annotations

import asyncio
import base64
import logging
import time

from sensehub.licensing.tier import feature_enabled
from sensehub.perception.camera import CameraService
from sensehub.perception.detector import YoloDetector
from sensehub.perception.gesture import GestureDetector
from sensehub.rules import engine as rule_engine

logger = logging.getLogger(__name__)


class CameraStreamBroadcaster:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._clients: set = set()
        self._lock = asyncio.Lock()

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
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            self._task = None

    async def _run(self, manager) -> None:
        cam = CameraService.get()
        try:
            if not cam.running:
                cam.start()
            YoloDetector.get().ensure_loaded()
            if feature_enabled("gesture_rules"):
                GestureDetector.get().ensure_loaded()
        except Exception as exc:
            await manager.broadcast({"type": "error", "message": str(exc)})
            return

        detector = YoloDetector.get()
        gesture_detector = GestureDetector.get() if feature_enabled("gesture_rules") else None
        loop = asyncio.get_running_loop()
        last_tick = time.perf_counter()
        frames = 0
        frame_idx = 0
        last_boxes: list = []
        last_gestures: list[dict] = []
        detect_every = 4
        gesture_every = 6

        try:
            while self._clients:
                frame = await loop.run_in_executor(None, cam.read)
                if frame is None:
                    await asyncio.sleep(0.05)
                    continue

                frame_idx += 1
                if frame_idx % detect_every == 0:
                    boxes = await loop.run_in_executor(
                        None,
                        lambda f=frame: detector.detect_persons(f, confidence_min=0.5),
                    )
                    last_boxes = boxes
                    if boxes:
                        best = max(boxes, key=lambda b: b.confidence)
                        await loop.run_in_executor(
                            None,
                            lambda b=best, n=len(boxes): rule_engine.handle_vision_event(
                                "person_detected",
                                confidence=b.confidence,
                                payload={"count": n},
                            ),
                        )

                if gesture_detector and frame_idx % gesture_every == 0:
                    try:
                        gestures = await loop.run_in_executor(
                            None,
                            lambda f=frame: gesture_detector.detect(f),
                        )
                        last_gestures = gestures
                        for gesture in gestures:
                            await loop.run_in_executor(
                                None,
                                lambda g=gesture: rule_engine.handle_gesture_event(
                                    g["gesture"],
                                    confidence=g["confidence"],
                                    payload=g,
                                ),
                            )
                    except Exception:
                        pass

                jpeg = await loop.run_in_executor(
                    None, lambda f=frame: cam.encode_jpeg(f, quality=55)
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
                    }
                )
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("camera broadcaster failed")
            await manager.broadcast({"type": "error", "message": str(exc)})
        finally:
            self._task = None


camera_broadcaster = CameraStreamBroadcaster()
