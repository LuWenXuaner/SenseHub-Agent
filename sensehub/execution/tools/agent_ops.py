"""Agent 任务类工具（须由大脑调用，禁止业务层直连）."""

from __future__ import annotations

from typing import Any

from sensehub.db import tasks as task_repo


def get_task_status(params: dict[str, Any]) -> dict[str, Any]:
    limit = int(params.get("limit", 5))
    tasks = task_repo.list_tasks(limit=limit)
    active = [t for t in tasks if t.status in ("running", "wait_confirm", "pending")]
    return {
        "active": [
            {
                "task_id": t.task_id,
                "status": t.status,
                "summary": t.summary or t.intent_text[:80],
                "intent": t.intent_text[:120],
            }
            for t in active
        ],
        "recent": [
            {
                "task_id": t.task_id,
                "status": t.status,
                "summary": t.summary or "",
                "intent": t.intent_text[:80],
            }
            for t in tasks[:3]
        ],
        "active_count": len(active),
    }


def cancel_tasks(params: dict[str, Any]) -> dict[str, Any]:
    from sensehub.orchestration.runner import cancel_task as cancel_one_task

    scope = str(params.get("scope", "active")).lower()
    tasks = task_repo.list_tasks(limit=20)
    cancelled: list[str] = []
    for t in tasks:
        if scope == "all":
            if t.status not in ("done", "failed", "cancelled"):
                cancel_one_task(t.task_id)
                cancelled.append(t.task_id)
        elif t.status in ("running", "wait_confirm", "pending"):
            cancel_one_task(t.task_id)
            cancelled.append(t.task_id)
    return {"cancelled_count": len(cancelled), "task_ids": cancelled, "scope": scope}
