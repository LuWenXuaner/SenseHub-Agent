"""任务编排服务."""

from __future__ import annotations

import uuid

from sensehub.cognition.brain import BrainPipelineError, format_brain_summary
from sensehub.db import tasks as task_repo
from sensehub.licensing.tier import check_text_quota, increment_text_usage
from sensehub.models.schemas import ExecutionPlan, TaskResponse
from sensehub.orchestration.graph import (
    GraphState,
    has_graph_checkpoint,
    resume_execution_graph,
    run_execution_graph,
)
from sensehub.orchestration.notify import notify, subscribe as _subscribe
from sensehub.security.audit import log_audit


def subscribe(listener) -> None:
    _subscribe(listener)


def _notify(task: TaskResponse) -> None:
    notify(task)


def _execution_state(
    task_id: str,
    intent_text: str,
    trace_id: str,
    plan_steps,
    *,
    needs_confirm: bool,
) -> GraphState:
    return {
        "task_id": task_id,
        "intent_text": intent_text,
        "trace_id": trace_id,
        "plan_steps": [s.model_dump() for s in plan_steps],
        "step_results": [],
        "current_step": 0,
        "status": "running",
        "error": None,
        "needs_confirm": needs_confirm,
    }


async def _execute_plan_fallback(task_id, steps, trace_id, intent_text) -> TaskResponse:
    """无 LangGraph checkpoint 时（如服务重启后）从 DB 恢复执行."""
    state = _execution_state(
        task_id,
        intent_text,
        trace_id,
        steps,
        needs_confirm=False,
    )
    run_execution_graph({**state, "needs_confirm": False})
    result = task_repo.get_task(task_id)
    assert result
    return result


async def run_task(task_id: str, intent_text: str, *, plan: ExecutionPlan | None = None) -> TaskResponse:
    trace_id = str(uuid.uuid4())
    ok, msg = check_text_quota()
    if not ok:
        task_repo.update_task(task_id, status="failed", error=msg)
        result = task_repo.get_task(task_id)
        assert result
        _notify(result)
        return result

    increment_text_usage()
    task_repo.update_task(task_id, status="running", trace_id=trace_id, summary="多脑协作规划中…")
    partial = task_repo.get_task(task_id)
    if partial:
        _notify(partial)

    try:
        if plan is None:
            from sensehub.gateway.agent_service import run_agent

            loop_out = await run_agent(intent_text, source="task")
            plan = loop_out["plan"]
            step_results = loop_out.get("step_results") or []
            reply = str(loop_out.get("answer") or "")
            status = "wait_confirm" if loop_out.get("needs_confirm") else "done"
            if not loop_out.get("needs_confirm") and step_results and not all(r.success for r in step_results):
                status = "failed"
            task_repo.update_task(
                task_id,
                status=status,
                summary=reply or plan.summary,
                plan_steps=plan.steps,
                current_step=len(plan.steps),
                step_results=step_results,
            )
            result = task_repo.get_task(task_id)
            assert result
            _notify(result)
            return result

        brain_agents = []
        log_audit(
            input_text=intent_text,
            action="brain_pipeline",
            result=plan.summary,
            trace_id=trace_id,
        )

        if not plan.steps:
            task_repo.update_task(task_id, status="failed", error="未能生成可执行步骤，请换种说法重试")
            result = task_repo.get_task(task_id)
            assert result
            _notify(result)
            return result

        needs_confirm = any(s.requires_confirm or s.risk_level == "L2" for s in plan.steps)
        summary_suffix = format_brain_summary(brain_agents) if brain_agents else "程序化规划"
        task_repo.update_task(
            task_id,
            summary=f"{plan.summary}（{summary_suffix}）",
            plan_steps=plan.steps,
            status="wait_confirm" if needs_confirm else "running",
        )

        state = _execution_state(
            task_id,
            intent_text,
            trace_id,
            plan.steps,
            needs_confirm=needs_confirm,
        )
        graph_result = run_execution_graph(state)

        if graph_result.get("__interrupt__"):
            task_repo.update_task(task_id, status="wait_confirm")
            result = task_repo.get_task(task_id)
            assert result
            _notify(result)
            return result

        result = task_repo.get_task(task_id)
        assert result
        if result.status == "done" and plan.steps:
            from sensehub.cognition.dispatch import synthesize_task_reply

            try:
                reply = await synthesize_task_reply(intent_text, plan, result)
                task_repo.update_task(task_id, summary=reply)
                result = task_repo.get_task(task_id)
                assert result
            except Exception:
                from sensehub.cognition.session_context import fallback_reply_from_task

                reply = fallback_reply_from_task(plan, result)
                task_repo.update_task(task_id, summary=reply)
                result = task_repo.get_task(task_id)
                assert result
        return result
    except BrainPipelineError as exc:
        task_repo.update_task(task_id, status="failed", error=str(exc))
        log_audit(input_text=intent_text, action="brain_pipeline_failed", result=str(exc), trace_id=trace_id)
        result = task_repo.get_task(task_id)
        assert result
        _notify(result)
        return result
    except Exception as exc:
        task_repo.update_task(task_id, status="failed", error=str(exc))
        log_audit(input_text=intent_text, action="task_failed", result=str(exc), trace_id=trace_id)
        result = task_repo.get_task(task_id)
        assert result
        _notify(result)
        return result


async def confirm_and_run(task_id: str) -> TaskResponse:
    task = task_repo.get_task(task_id)
    if not task or task.status != "wait_confirm":
        raise ValueError("任务不在待确认状态")

    from sensehub.security.sandbox import grant_paths_on_confirm

    grant_paths_on_confirm(task.plan_steps)

    if has_graph_checkpoint(task_id):
        resume_execution_graph(task_id, resume_value={"approved": True})
    else:
        await _execute_plan_fallback(task_id, task.plan_steps, task.trace_id, task.intent_text)

    result = task_repo.get_task(task_id)
    assert result
    return result


def cancel_task(task_id: str) -> TaskResponse | None:
    from sensehub.execution.kill_switch import activate

    activate()
    task = task_repo.get_task(task_id)
    if not task or task.status in ("done", "failed", "cancelled"):
        return task
    task_repo.update_task(task_id, status="cancelled")
    result = task_repo.get_task(task_id)
    if result:
        _notify(result)
    return result
