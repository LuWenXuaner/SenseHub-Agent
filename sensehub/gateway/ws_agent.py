"""Agent 执行过程 WebSocket."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from sensehub.gateway.events import subscribe, unsubscribe
from sensehub.security.auth import decode_token

router = APIRouter()


class AgentConnectionManager:
    def __init__(self) -> None:
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, ws: WebSocket, session_id: str) -> None:
        await ws.accept()
        self.active.setdefault(session_id or "__all__", []).append(ws)

    def disconnect(self, ws: WebSocket, session_id: str) -> None:
        key = session_id or "__all__"
        if key in self.active and ws in self.active[key]:
            self.active[key].remove(ws)

    async def broadcast(self, data: dict) -> None:
        sid = str(data.get("session_id") or "")
        targets = list(self.active.get(sid, [])) + list(self.active.get("__all__", []))
        dead: list[tuple[WebSocket, str]] = []
        for ws in targets:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append((ws, sid))
        for ws, key in dead:
            self.disconnect(ws, key)


agent_manager = AgentConnectionManager()


def _bridge_event(event: dict) -> None:
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(agent_manager.broadcast(event))
    except RuntimeError:
        pass


subscribe(_bridge_event)


@router.websocket("/ws/agent")
async def ws_agent(ws: WebSocket, token: str = "", session_id: str = ""):
    if not decode_token(token):
        await ws.close(code=4401)
        return
    await agent_manager.connect(ws, session_id)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        agent_manager.disconnect(ws, session_id)
