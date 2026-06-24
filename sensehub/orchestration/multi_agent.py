"""多 Agent 协调：多脑规划 → 逐步执行（含视觉 Agent）."""

from __future__ import annotations

import uuid
from typing import Any

from sensehub.cognition.brain import BrainPipelineError, format_brain_summary, orchestrate_brains
from sensehub.cognition.vision_agent import run_gui_agent
from sensehub.execution.tools.registry import execute_step
from sensehub.licensing.tier import feature_enabled
from sensehub.models.schemas import ExecutionPlan, StepResult
from sensehub.security.audit import log_audit


async def execute_plan(plan, intent: str, agents: list[dict[str, Any]]) -> tuple[list[Any], list[dict[str, Any]]]:
    results: list[Any] = []
    for step in plan.steps:
        if step.tool == "gui_agent":
            out = await run_gui_agent(
                step.params.get("intent", intent),
                max_steps=int(step.params.get("max_steps", 10)),
            )
            results.append(out)
            if not out.get("success"):
                return results, agents
        else:
            r = execute_step(step)
            results.append(r.model_dump())
            if not r.success:
                return results, agents
    agents.append({"role": "executor", "steps_done": len(results)})
    return results, agents


async def run_multi_agent(
    intent: str,
    *,
    plan: ExecutionPlan | None = None,
    agents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not feature_enabled("multi_agent"):
        raise RuntimeError("多 Agent 协调需要 Max 档位")

    trace_id = str(uuid.uuid4())
    try:
        if plan is None:
            plan, agents = await orchestrate_brains(intent)
        else:
            agents = list(agents or [])
    except BrainPipelineError as exc:
        return {"success": False, "error": str(exc), "agents": exc.agents, "method": "multi-agent"}

    log_audit(
        input_text=intent,
        action="brain_pipeline",
        result=format_brain_summary(agents),
        trace_id=trace_id,
    )

    results, agents = await execute_plan(plan, intent, agents)
    last = results[-1] if results else {}
    success = bool(last.get("success")) if isinstance(last, dict) else False
    if not success and results:
        err = last.get("error") if isinstance(last, dict) else "执行失败"
        return {
            "success": False,
            "error": err,
            "agents": agents,
            "results": results,
            "plan": plan.model_dump(),
            "method": "multi-agent",
        }

    log_audit(input_text=intent, action="multi_agent_complete", result="done", trace_id=trace_id)
    return {
        "success": True,
        "intent": intent,
        "agents": agents,
        "results": results,
        "plan": plan.model_dump(),
        "summary": format_brain_summary(agents),
        "method": "multi-agent",
    }


async def run_multi_agent_task(
    task_id: str,
    intent_text: str,
    *,
    plan: ExecutionPlan | None = None,
    agents: list[dict[str, Any]] | None = None,
):
    from sensehub.db import tasks as task_repo
    from sensehub.models.schemas import TaskResponse
    from sensehub.orchestration.notify import notify

    task_repo.update_task(task_id, status="running", summary="多脑协作规划中…")
    partial = task_repo.get_task(task_id)
    if partial:
        notify(partial)
    try:
        result = await run_multi_agent(intent_text, plan=plan, agents=agents)
        if result.get("success"):
            from sensehub.models.schemas import PlanStep

            plan_data = result.get("plan") or {}
            plan_steps = [PlanStep(**s) for s in plan_data.get("steps", [])]
            step_results: list[StepResult] = []
            for i, item in enumerate(result.get("results", []), start=1):
                if isinstance(item, dict) and "step_id" not in item:
                    step_results.append(
                        StepResult(
                            step_id=i,
                            success=bool(item.get("success")),
                            output=item,
                            screenshot_path=item.get("screenshot_path"),
                            error=None if item.get("success") else item.get("error"),
                        )
                    )
                elif isinstance(item, dict):
                    step_results.append(
                        StepResult(
                            step_id=item.get("step_id", i),
                            success=bool(item.get("success")),
                            output=item.get("output", item),
                            error=item.get("error"),
                        )
                    )
            task_repo.update_task(
                task_id,
                status="done",
                summary=result.get("summary") or "多脑协作完成",
                plan_steps=plan_steps,
                step_results=step_results,
            )
        else:
            task_repo.update_task(
                task_id,
                status="failed",
                error=result.get("error", "失败"),
                summary=format_brain_summary(result.get("agents") or []),
            )
    except Exception as exc:
        task_repo.update_task(task_id, status="failed", error=str(exc), summary="多脑协作异常")
    final = task_repo.get_task(task_id)
    if final:
        notify(final)
    return final
