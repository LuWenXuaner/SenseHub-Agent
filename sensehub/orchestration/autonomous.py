"""OpenClaw 风格多步自主执行：子目标均走 Gateway AgentRuntime."""

from __future__ import annotations

import re
from typing import Any

from sensehub.db import tasks as task_repo
from sensehub.gateway.agent_service import run_agent
from sensehub.models.schemas import StepResult
from sensehub.orchestration.notify import notify
from sensehub.security.audit import log_audit


def _split_goals(intent: str) -> list[str]:
    parts = re.split(r"[；;。]|然后|并且|接着|再", intent)
    goals = [p.strip() for p in parts if p.strip()]
    return goals or [intent.strip()]


async def run_autonomous(intent: str, *, max_steps_per_goal: int = 12) -> dict[str, Any]:
    goals = _split_goals(intent)
    all_agents: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    for idx, goal in enumerate(goals, start=1):
        loop_out = await run_agent(goal, source="autonomous")
        agents = loop_out.get("agents") or []
        all_agents.extend(agents)
        step_results = loop_out.get("step_results") or []
        success = bool(loop_out.get("executed")) and (
            all(r.success for r in step_results) if step_results else bool(loop_out.get("answer"))
        )
        item = {
            "goal_index": idx,
            "goal": goal,
            "plan_summary": loop_out.get("plan").summary if loop_out.get("plan") else goal,
            "results": [r.model_dump() if isinstance(r, StepResult) else r for r in step_results],
            "success": success,
            "answer": loop_out.get("answer", ""),
        }
        if not success:
            failed = [r for r in step_results if not r.success]
            item["error"] = failed[-1].error if failed else "未完成"
            results.append(item)
            break
        results.append(item)

    success = all(r.get("success") for r in results) and len(results) == len(goals)
    done_count = len([r for r in results if r.get("success")])
    return {
        "success": success,
        "intent": intent,
        "goals": goals,
        "results": results,
        "agents": all_agents,
        "summary": f"自主执行 {done_count}/{len(goals)}（AgentRuntime）",
        "method": "autonomous-runtime",
    }


async def run_autonomous_task(task_id: str, intent_text: str) -> None:
    task_repo.update_task(task_id, status="running", summary="自主 Agent：Gateway 执行中…")
    partial = task_repo.get_task(task_id)
    if partial:
        notify(partial)

    try:
        out = await run_autonomous(intent_text)
        status = "done" if out.get("success") else "failed"
        summary = out.get("summary", "")
        if out.get("results"):
            last = out["results"][-1]
            if last.get("answer"):
                summary = str(last["answer"])
        task_repo.update_task(
            task_id,
            status=status,
            summary=summary,
            error=None if status == "done" else str(out.get("results", [{}])[-1].get("error", "失败")),
        )
        log_audit(input_text=intent_text, action="autonomous", result=summary[:200])
    except Exception as exc:
        task_repo.update_task(task_id, status="failed", error=str(exc))
    result = task_repo.get_task(task_id)
    if result:
        notify(result)
