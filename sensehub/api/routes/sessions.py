"""会话 API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sensehub.api.deps import get_current_user
from sensehub.db import sessions as session_repo

router = APIRouter(tags=["sessions"])


@router.get("/sessions")
async def list_sessions(channel: str | None = None, _: str = Depends(get_current_user)):
    ch = channel if channel in ("hub", "studio") else None
    return {"sessions": session_repo.list_sessions(channel=ch)}


@router.post("/sessions")
async def create_session(body: dict | None = None, _: str = Depends(get_current_user)):
    title = ""
    ch = "hub"
    if body and isinstance(body, dict):
        title = str(body.get("title", "")).strip()
        raw_ch = str(body.get("channel", "hub")).strip()
        if raw_ch in ("hub", "studio"):
            ch = raw_ch
    sid = session_repo.create_session(title=title or "新会话", channel=ch)
    return {"session_id": sid, "title": title or "新会话", "channel": ch}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, _: str = Depends(get_current_user)):
    sess = session_repo.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = session_repo.load_messages_for_ui(session_id)
    return {"session": sess, "messages": messages}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, _: str = Depends(get_current_user)):
    if not session_repo.delete_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}
