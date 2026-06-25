"""规则匹配与动作执行."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from sensehub.execution.tools.registry import execute_step
from sensehub.licensing.tier import feature_enabled, get_tier
from sensehub.models.schemas import PlanStep
from sensehub.perception.events import log_event
from sensehub.rules import store as rule_store

_event_listeners: list[Callable[[dict[str, Any]], None]] = []
_person_cooldown: dict[str, float] = {}
_COOLDOWN_SEC = 8.0


def subscribe(listener: Callable[[dict[str, Any]], None]) -> None:
    _event_listeners.append(listener)


def _notify(payload: dict[str, Any]) -> None:
    for fn in _event_listeners:
        try:
            fn(payload)
        except Exception:
            pass


def _tier_ok(rule_tier: str) -> bool:
    order = {"lite": 0, "pro": 1, "max": 2}
    return order.get(get_tier(), 0) >= order.get(rule_tier, 0)


def handle_gesture_event(
    gesture_name: str,
    *,
    confidence: float,
    payload: dict | None = None,
) -> list[dict[str, Any]]:
    if not feature_enabled("gesture_rules"):
        return []
    import time

    triggered: list[dict[str, Any]] = []
    now = time.time()
    for rule in rule_store.list_rules():
        if not rule.enabled or not _tier_ok(rule.tier_min):
            continue
        trig = rule.trigger
        if trig.type != "gesture" or trig.event != gesture_name:
            continue
        if confidence < trig.confidence_min:
            continue
        key = f"{rule.rule_id}:{gesture_name}"
        last = _person_cooldown.get(key, 0)
        if now - last < _COOLDOWN_SEC:
            continue
        _person_cooldown[key] = now
        result = _run_action(rule, payload or {"gesture": gesture_name, "confidence": confidence})
        triggered.append(result)
    return triggered


def handle_vision_event(
    event_name: str,
    *,
    confidence: float,
    payload: dict | None = None,
) -> list[dict[str, Any]]:
    import time

    triggered: list[dict[str, Any]] = []
    now = time.time()
    for rule in rule_store.list_rules():
        if not rule.enabled or not _tier_ok(rule.tier_min):
            continue
        trig = rule.trigger
        if trig.type != "vision" or trig.event != event_name:
            continue
        if confidence < trig.confidence_min:
            continue
        key = f"{rule.rule_id}:{event_name}"
        last = _person_cooldown.get(key, 0)
        if now - last < _COOLDOWN_SEC:
            continue
        _person_cooldown[key] = now
        result = _run_action(rule, payload or {"confidence": confidence})
        triggered.append(result)
    return triggered


def handle_speech_text(text: str) -> dict[str, Any] | None:
    normalized = text.strip()
    for rule in rule_store.list_rules():
        if not rule.enabled or not _tier_ok(rule.tier_min):
            continue
        trig = rule.trigger
        if trig.type != "speech" or not trig.match:
            continue
        if trig.match not in normalized and normalized not in trig.match:
            continue
        return _run_action(rule, {"text": normalized}, speech_bypass=trig.bypass_llm)
    return None


def _schedule_confirm_pending() -> dict[str, Any]:
    from sensehub.db import tasks as task_repo
    from sensehub.orchestration.runner import confirm_and_run

    tasks = task_repo.list_tasks(15)
    pending = [t for t in tasks if t.status == "wait_confirm"]
    if not pending:
        return {"ok": False, "reason": "no_wait_confirm_task"}
    task = pending[0]

    async def _run() -> None:
        await confirm_and_run(task.task_id)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run())
    except RuntimeError:
        asyncio.run(_run())
    return {"ok": True, "task_id": task.task_id}


def _cancel_latest_pending() -> dict[str, Any]:
    from sensehub.db import tasks as task_repo
    from sensehub.orchestration.runner import cancel_task

    tasks = task_repo.list_tasks(15)
    for t in tasks:
        if t.status == "wait_confirm":
            cancel_task(t.task_id)
            return {"ok": True, "task_id": t.task_id}
    return {"ok": False, "reason": "no_wait_confirm_task"}


def _run_action(
    rule,
    payload: dict,
    *,
    speech_bypass: bool = False,
) -> dict[str, Any]:
    action = rule.action
    if action.type == "notify":
        event = log_event(
            event_type="rule_triggered",
            source="rules",
            rule_id=rule.rule_id,
            message=action.message or rule.name,
            payload=payload,
        )
        msg = {
            "type": "rule_triggered",
            "rule_id": rule.rule_id,
            "name": rule.name,
            "message": event.message,
            "event": event.model_dump(),
        }
        _notify(msg)
        return msg

    if action.type == "confirm_pending":
        out = _schedule_confirm_pending()
        msg = action.message or rule.name
        if not out.get("ok"):
            msg = f"{msg}（当前无待确认任务）"
        event = log_event(
            event_type="rule_triggered",
            source="rules",
            rule_id=rule.rule_id,
            message=msg,
            payload={**payload, **out},
        )
        body = {
            "type": "rule_triggered",
            "rule_id": rule.rule_id,
            "name": rule.name,
            "message": event.message,
            "event": event.model_dump(),
        }
        _notify(body)
        return body

    if action.type == "cancel_pending":
        out = _cancel_latest_pending()
        msg = action.message or rule.name
        if not out.get("ok"):
            msg = f"{msg}（当前无待确认任务）"
        event = log_event(
            event_type="rule_triggered",
            source="rules",
            rule_id=rule.rule_id,
            message=msg,
            payload={**payload, **out},
        )
        body = {
            "type": "rule_triggered",
            "rule_id": rule.rule_id,
            "name": rule.name,
            "message": event.message,
            "event": event.model_dump(),
        }
        _notify(body)
        return body

    if action.type == "macro" and action.steps:
        if speech_bypass:
            event = log_event(
                event_type="rule_skipped",
                source="rules",
                rule_id=rule.rule_id,
                message="语音规则捷径已禁用，请由大脑 Agent 处理",
                payload=payload,
            )
            msg = {
                "type": "rule_skipped",
                "rule_id": rule.rule_id,
                "name": rule.name,
                "message": event.message,
            }
            _notify(msg)
            return msg
        results = []
        for raw in action.steps:
            step = PlanStep(
                step_id=raw.get("step_id", 1),
                tool=raw["tool"],
                params=raw.get("params", {}),
                risk_level=raw.get("risk_level", "L1"),
                description=raw.get("description", raw["tool"]),
            )
            results.append(execute_step(step))
        event = log_event(
            event_type="rule_triggered",
            source="rules",
            rule_id=rule.rule_id,
            message=f"宏已执行: {rule.name}",
            payload={"steps": len(results), "success": all(r.success for r in results)},
        )
        msg = {
            "type": "rule_triggered",
            "rule_id": rule.rule_id,
            "name": rule.name,
            "message": event.message,
            "event": event.model_dump(),
        }
        _notify(msg)
        return msg

    return {"type": "rule_skipped", "rule_id": rule.rule_id}


async def run_voice_command(
    text: str,
    *,
    history: list[dict[str, Any]] | None = None,
    session_id: str = "",
) -> dict[str, Any]:
    """语音/文本：交给意图脑分流（问答 / 查状态 / 取消 / 执行任务）."""
    from sensehub.cognition.brain import BrainPipelineError
    from sensehub.cognition.dispatch import (
        enrich_agents_with_task,
        process_user_input,
        synthesize_task_reply,
    )
    from sensehub.db import tasks as task_repo
    from sensehub.models.schemas import ExecutionPlan
    from sensehub.orchestration.multi_agent import run_multi_agent_task
    from sensehub.orchestration.runner import run_task

    try:
        result = await process_user_input(text, source="voice", history=history, session_id=session_id or "")
    except BrainPipelineError as exc:
        return {"text": text, "matched": False, "message": str(exc), "task_id": None, "action": "error"}

    action = result.get("action")
    if action in ("answer", "status", "cancel"):
        return {
            "text": text,
            "matched": True,
            "task_id": None,
            "message": result.get("message", ""),
            "reply": result.get("reply"),
            "action": action,
            "agents": result.get("agents", []),
        }

    if action == "error":
        return {
            "text": text,
            "matched": False,
            "message": result.get("message", "处理失败"),
            "task_id": None,
            "action": "error",
        }

    plan = result.get("plan")
    if not plan:
        return {"text": text, "matched": False, "message": "未能生成计划", "task_id": None, "action": "error"}
    if isinstance(plan, dict):
        plan = ExecutionPlan(**plan)

    if result.get("executed"):
        reply = str(result.get("reply") or "")
        task_id = task_repo.create_task(f"[语音] {text}")
        step_results = result.get("step_results") or []
        task_repo.update_task(
            task_id,
            status="done",
            summary=reply,
            plan_steps=plan.steps,
            current_step=len(plan.steps),
            step_results=step_results,
        )
        task = task_repo.get_task(task_id)
        agents = enrich_agents_with_task(list(result.get("agents") or []), plan, task)
        return {
            "text": text,
            "matched": True,
            "task_id": task_id,
            "message": reply,
            "reply": reply,
            "action": "execute",
            "agents": agents,
            "task": task.model_dump() if task else None,
        }

    needs_confirm = any(s.requires_confirm for s in plan.steps)
    task_id = task_repo.create_task(f"[语音] {text}")
    if needs_confirm:
        if feature_enabled("multi_agent"):
            asyncio.create_task(run_multi_agent_task(task_id, text, plan=plan, agents=result.get("agents")))
        else:
            asyncio.create_task(run_task(task_id, text, plan=plan))
        msg = result.get("message") or "任务需确认后执行"
        return {
            "text": text,
            "matched": True,
            "task_id": task_id,
            "message": msg,
            "action": "execute",
            "agents": result.get("agents", []),
        }

    agents = list(result.get("agents") or [])
    if feature_enabled("multi_agent"):
        task = await run_multi_agent_task(task_id, text, plan=plan, agents=agents)
    else:
        task = await run_task(task_id, text, plan=plan)
    agents = enrich_agents_with_task(agents, plan, task)
    reply = await synthesize_task_reply(text, plan, task, agents=agents, history=history)
    return {
        "text": text,
        "matched": True,
        "task_id": task_id,
        "message": reply,
        "reply": reply,
        "action": "execute",
        "agents": agents,
        "task": task.model_dump() if task else None,
    }
