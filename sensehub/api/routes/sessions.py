"""会话 API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sensehub.api.deps import get_current_user
from sensehub.db import sessions as session_repo
from sensehub.db import users as user_store

router = APIRouter(tags=["sessions"])


def _user_id(username: str) -> str:
    user = user_store.get_user(username.strip().lower())
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return str(user["user_id"])


def _require_session(session_id: str, user_id: str) -> dict:
    sess = session_repo.get_session(session_id)
    if not sess or str(sess.get("user_id")) != user_id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return sess


@router.get("/sessions")
async def list_sessions(channel: str | None = None, username: str = Depends(get_current_user)):
    uid = _user_id(username)
    ch = channel if channel in ("hub", "studio") else None
    return {"sessions": session_repo.list_sessions(user_id=uid, channel=ch)}


@router.post("/sessions")
async def create_session(body: dict | None = None, username: str = Depends(get_current_user)):
    uid = _user_id(username)
    title = ""
    ch = "hub"
    if body and isinstance(body, dict):
        title = str(body.get("title", "")).strip()
        raw_ch = str(body.get("channel", "hub")).strip()
        if raw_ch in ("hub", "studio"):
            ch = raw_ch
    sid = session_repo.create_session(user_id=uid, title=title or "新会话", channel=ch)
    return {"session_id": sid, "title": title or "新会话", "channel": ch}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, username: str = Depends(get_current_user)):
    uid = _user_id(username)
    _require_session(session_id, uid)
    messages = session_repo.load_messages_for_ui(session_id)
    sess = session_repo.get_session(session_id)
    return {"session": sess, "messages": messages}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, username: str = Depends(get_current_user)):
    uid = _user_id(username)
    _require_session(session_id, uid)
    if not session_repo.delete_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}
