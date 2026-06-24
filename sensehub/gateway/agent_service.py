"""Gateway Agent 服务：会话串行 + 消息持久化."""

from __future__ import annotations

from typing import Any

from sensehub.db import sessions as session_repo
from sensehub.gateway.session_lane import lane_lock
from sensehub.runtime.agent_runtime import AgentRuntime


async def run_agent(
    user_text: str,
    *,
    session_id: str = "",
    user_id: str = "local",
    source: str = "text",
    history: list[dict[str, Any]] | None = None,
    intent_raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sid = session_id.strip()
    if not sid:
        sid = session_repo.create_session(user_id=user_id, title=user_text[:40])

    async with lane_lock(sid):
        if history:
            transcript = history
        else:
            transcript = session_repo.load_transcript(sid, limit=24)

        session_repo.append_message(sid, role="user", content=user_text, meta={"source": source})

        result = await AgentRuntime.run(
            user_text,
            history=transcript,
            intent_raw=intent_raw,
            session_id=sid,
        )

        reply = str(result.get("answer") or "")
        if reply:
            session_repo.append_message(
                sid,
                role="assistant",
                content=reply,
                meta={
                    "executed": result.get("executed"),
                    "needs_confirm": result.get("needs_confirm"),
                },
            )
        session_repo.touch_session(sid, title=user_text[:40])

    result["session_id"] = sid
    return result
