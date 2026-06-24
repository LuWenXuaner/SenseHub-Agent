"""WebSocket：任务状态 + 摄像头帧流."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from sensehub.api.camera_broadcaster import camera_broadcaster
from sensehub.db import tasks as task_repo
from sensehub.licensing.tier import feature_enabled
from sensehub.orchestration import runner
from sensehub.perception.virtual_session import VirtualScreenSession
from sensehub.rules import engine as rule_engine
from sensehub.security.auth import decode_token

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict) -> None:
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


class CameraConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict) -> None:
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


task_manager = ConnectionManager()
camera_manager = CameraConnectionManager()


def _on_task_update(task) -> None:
    payload = task.model_dump()
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(task_manager.broadcast({"type": "task_update", "task": payload}))
    except RuntimeError:
        pass


def _on_rule_event(payload: dict) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(camera_manager.broadcast(payload))
    except RuntimeError:
        pass


runner.subscribe(_on_task_update)
rule_engine.subscribe(_on_rule_event)


@router.websocket("/ws/tasks")
async def ws_tasks(websocket: WebSocket, token: str | None = None):
    if not token or not decode_token(token):
        await websocket.close(code=4401)
        return
    await task_manager.connect(websocket)
    try:
        tasks = task_repo.list_tasks(10)
        await websocket.send_json(
            {"type": "snapshot", "tasks": [t.model_dump() for t in tasks]}
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        task_manager.disconnect(websocket)


@router.websocket("/ws/camera")
async def ws_camera(websocket: WebSocket, token: str | None = None):
    if not token or not decode_token(token):
        await websocket.close(code=4401)
        return

    await websocket.accept()
    camera_broadcaster.attach(websocket, camera_manager)
    await camera_broadcaster.ensure_running(camera_manager)
    await websocket.send_json({"type": "status", "running": True})

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        camera_broadcaster.detach(websocket, camera_manager)
        await camera_broadcaster.stop_if_idle()


@router.websocket("/ws/voice/stream")
async def ws_voice_stream(websocket: WebSocket, token: str | None = None):
    if not token or not decode_token(token):
        await websocket.close(code=4401)
        return
    if not feature_enabled("voice_stream"):
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "流式 ASR 需要 Pro 档位"})
        await websocket.close(code=4403)
        return

    await websocket.accept()
    buffer = bytearray()
    loop = asyncio.get_running_loop()
    await websocket.send_json({"type": "ready"})

    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") != "websocket.receive":
                continue
            if msg.get("bytes"):
                buffer.extend(msg["bytes"])
                continue
            if msg.get("text"):
                import json

                data = json.loads(msg["text"])
                if data.get("type") == "end":
                    if not buffer:
                        await websocket.send_json({"type": "final", "text": ""})
                        continue
                    from sensehub.perception.asr import transcribe_bytes

                    text, duration_ms = await loop.run_in_executor(
                        None,
                        lambda b=bytes(buffer): transcribe_bytes(b, suffix=".webm"),
                    )
                    buffer.clear()
                    await websocket.send_json(
                        {"type": "final", "text": text, "duration_ms": duration_ms}
                    )
                elif data.get("type") == "reset":
                    buffer.clear()
                    await websocket.send_json({"type": "reset", "ok": True})
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/virtual-screen/live")
async def ws_virtual_screen_live(websocket: WebSocket, token: str | None = None):
    if not token or not decode_token(token):
        await websocket.close(code=4401)
        return
    if not feature_enabled("virtual_screen"):
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "虚拟屏需要 Max 档位"})
        await websocket.close(code=4403)
        return

    await websocket.accept()
    await websocket.send_json({"type": "status", **VirtualScreenSession.status()})

    try:
        while True:
            if not VirtualScreenSession.is_active():
                await asyncio.sleep(0.1)
                try:
                    msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                    import json

                    data = json.loads(msg)
                    if data.get("type") == "ping":
                        await websocket.send_json({"type": "status", **VirtualScreenSession.status()})
                except (asyncio.TimeoutError, WebSocketDisconnect):
                    pass
                continue

            payload = await VirtualScreenSession.tick()
            if payload:
                await websocket.send_json(payload)
            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        pass
