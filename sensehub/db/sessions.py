"""会话 transcript SQLite 持久化."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sensehub.db.database import get_connection


def create_session(*, user_id: str = "local", title: str = "新会话", channel: str = "hub") -> str:
    sid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    ch = channel if channel in ("hub", "studio") else "hub"
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (session_id, user_id, title, channel, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (sid, user_id, title[:120], ch, now, now),
        )
    return sid


def touch_session(session_id: str, *, title: str | None = None) -> None:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        if title:
            conn.execute(
                "UPDATE sessions SET updated_at = ?, title = ? WHERE session_id = ?",
                (now, title[:120], session_id),
            )
        else:
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )


def list_sessions(*, user_id: str = "local", limit: int = 40, channel: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if channel:
            rows = conn.execute(
                "SELECT session_id, title, channel, created_at, updated_at FROM sessions WHERE user_id = ? AND channel = ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, channel, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT session_id, title, channel, created_at, updated_at FROM sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def delete_session(session_id: str) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cur = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        return cur.rowcount > 0


def get_session(session_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT session_id, user_id, title, created_at, updated_at FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def append_message(
    session_id: str,
    *,
    role: str,
    content: str,
    task_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> str:
    mid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (message_id, session_id, role, content, task_id, meta_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                mid,
                session_id,
                role,
                content,
                task_id,
                json.dumps(meta or {}, ensure_ascii=False),
                now,
            ),
        )
    return mid


def load_transcript(session_id: str, *, limit: int = 24) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content, meta_json FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows[-limit:]:
        item = {"role": row["role"], "content": row["content"]}
        meta_raw = row["meta_json"]
        if meta_raw:
            try:
                meta = json.loads(meta_raw)
                if isinstance(meta, dict) and meta.get("task"):
                    item["task"] = meta["task"]
            except json.JSONDecodeError:
                pass
        out.append(item)
    return out


def load_messages_for_ui(session_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT message_id, role, content, task_id, meta_json, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    result = []
    for row in rows:
        meta = {}
        if row["meta_json"]:
            try:
                meta = json.loads(row["meta_json"])
            except json.JSONDecodeError:
                meta = {}
        result.append(
            {
                "id": row["message_id"],
                "role": row["role"],
                "content": row["content"],
                "task_id": row["task_id"],
                "meta": meta,
                "created_at": row["created_at"],
            }
        )
    return result
