"""用户输入唯一入口：意图脑 → Harness 路由 → Gateway AgentRuntime（OpenClaw 单循环）."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from sensehub.cognition.brain import BrainPipelineError
from sensehub.cognition.chat_harness import run_chat_harness
from sensehub.cognition.code_harness import run_code_harness
from sensehub.cognition.console_harness import reconcile_route
from sensehub.cognition.prompts import INTENT_SYSTEM
from sensehub.cognition.quick_match import match_atomic_plan, match_quick_plan
from sensehub.cognition.router import LLMRouter
from sensehub.cognition.chat_errors import (
    ChatModelUnavailableError,
    CHAT_MODEL_UNAVAILABLE_MSG,
    assert_chat_route_ready,
    normalize_chat_model_error,
)
from sensehub.cognition.studio_models import StudioModelError, resolve_studio_model
from sensehub.cognition.session_context import (
    fallback_reply_from_task,
    format_history_for_brain,
)
from sensehub.models.schemas import ExecutionPlan, TaskResponse
from sensehub.security.audit import log_audit

_WAKE_PREFIX = re.compile(
    r"^(?:(?:灵|零|凌|领|令|林)(?:枢|书|疏|舒|数)|领悟|灵枢)"
    r"(?:帮我|请|啊|呀|呢)?\s*",
    re.I,
)

_CONVERSATION_SYSTEM = """你是灵枢智能助手。自然、友好地回答用户问题。
这是控制台对话模式：只输出文字答复，不调用桌面/浏览器工具。
若用户需要实际操作电脑，可提示其用更具体的任务描述。"""


def _is_pure_conversation(intent_raw: dict[str, Any]) -> bool:
    mode = str(intent_raw.get("action_mode", "")).lower()
    if mode != "answer":
        return False
    wants = str(intent_raw.get("user_wants", "")).lower()
    if wants == "desktop_action":
        return False
    suggested = intent_raw.get("suggested_tools")
    if isinstance(suggested, list) and suggested:
        return False
    intent_type = str(intent_raw.get("intent_type", "")).lower()
    if intent_type in {"desktop", "browser", "file", "virtual"}:
        return False
    return True


async def _answer_conversation(
    text: str,
    *,
    history: list[dict[str, Any]] | None,
    session_id: str,
    intent_raw: dict[str, Any],
    agents: list[dict[str, Any]],
) -> dict[str, Any]:
    router = LLMRouter()
    hist_block = format_history_for_brain(history)
    user_content = f"{hist_block}\n\n用户：{text}" if hist_block else text
    try:
        answer = await router.chat(
            "intent",
            [
                {"role": "system", "content": _CONVERSATION_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.6,
            max_tokens=4096,
        )
    except Exception as exc:
        raise BrainPipelineError(f"对话脑不可用: {exc}") from exc
    answer = str(answer or "").strip() or "抱歉，我暂时无法回答。"
    agents.append({"role": "conversation", "model_role": "intent", "preview": answer[:80]})
    plan = ExecutionPlan(summary="对话", steps=[])
    log_audit(input_text=text, action="brain_conversation", result=answer[:200])
    return {
        "action": "answer",
        "matched": True,
        "executed": True,
        "plan": plan,
        "step_results": [],
        "reply": answer,
        "agents": agents,
        "intent_raw": intent_raw,
        "message": answer,
        "session_id": session_id,
    }


def _step_results_all_ok(results: list[Any]) -> bool:
    if not results:
        return False
    for r in results:
        ok = bool(getattr(r, "success", False)) if not isinstance(r, dict) else bool(r.get("success"))
        if not ok:
            return False
    return True


def _maybe_save_plan_cache(text: str, plan: ExecutionPlan, intent_raw: dict[str, Any] | None, results: list[Any]) -> None:
    if not _step_results_all_ok(results):
        return
    from sensehub.cognition.plan_cache import save_success_plan

    save_success_plan(text, plan, intent_raw)


def _append_safety_agent(agents: list[dict[str, Any]], plan: ExecutionPlan) -> None:
    if not plan.steps or any(a.get("role") == "safety" for a in agents):
        return
    from sensehub.cognition.safety import SafetyReviewer

    safety = SafetyReviewer().score(plan)
    agents.append(
        {
            "role": "safety",
            "model_role": "safety",
            "passed": safety.passed,
            "reason": safety.reason,
            "scores": safety.model_dump(),
        }
    )


def _quick_plan_enabled() -> bool:
    val = os.getenv("SENSEHUB_ENABLE_QUICK_PLAN", "").strip().lower()
    return val in {"1", "true", "yes", "on"}


def normalize_user_text(raw: str) -> str:
    """仅去掉唤醒词前缀，不改变语义；路由决策由意图脑 + Harness 完成."""
    text = raw.strip().replace("\u3000", " ")
    stripped = _WAKE_PREFIX.sub("", text).strip()
    return stripped or text


def enrich_agents_with_task(
    agents: list[dict[str, Any]] | None,
    plan: ExecutionPlan,
    task: TaskResponse,
) -> list[dict[str, Any]]:
    """补齐 executor 轨迹；AgentRuntime 已记录过的步骤不再重复追加."""
    out = list(agents or [])
    if sum(1 for a in out if a.get("role") == "executor") >= len(plan.steps):
        return out
    logged = {
        (str(a.get("tool")), int(a.get("step_id")))
        for a in out
        if a.get("role") == "executor" and a.get("step_id") is not None
    }
    for step in plan.steps:
        key = (step.tool, step.step_id)
        if key in logged:
            continue
        result = next((r for r in task.step_results if r.step_id == step.step_id), None)
        out.append(
            {
                "role": "executor",
                "step_id": step.step_id,
                "tool": step.tool,
                "description": step.description,
                "success": result.success if result else False,
                "output": result.output if result else {},
                "error": result.error if result else None,
            }
        )
    return out


def _history_payload(history: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not history:
        return []
    return [h for h in history if isinstance(h, dict) and str(h.get("content", "")).strip()]


from sensehub.cognition.reply_synthesis import synthesize_task_reply_from_models as synthesize_task_reply


async def process_studio_chat(
    user_text: str,
    *,
    history: list[dict[str, Any]] | None = None,
    session_id: str = "",
    user_id: str = "",
    model_id: str = "",
) -> dict[str, Any]:
    """Studio 纯对话：仅应答，不触发桌面/浏览器执行."""
    from sensehub.runtime.request_context import set_llm_usage_user

    if user_id:
        set_llm_usage_user(user_id)
    raw = user_text.strip()
    if not raw:
        raise BrainPipelineError("内容不能为空")

    text = normalize_user_text(raw)
    hist = _history_payload(history)

    selected_id = (model_id or "").strip()
    route = None
    if selected_id:
        try:
            route = resolve_studio_model(selected_id)
        except StudioModelError as exc:
            raise BrainPipelineError(str(exc)) from exc
        if route and not route.available:
            raise BrainPipelineError(route.reason or CHAT_MODEL_UNAVAILABLE_MSG)

    assert_chat_route_ready(route)

    try:
        harness_out = await run_chat_harness(text, history=hist, route=route)
    except ChatModelUnavailableError as exc:
        raise BrainPipelineError(CHAT_MODEL_UNAVAILABLE_MSG) from exc
    except BrainPipelineError:
        raise
    except Exception as exc:
        msg = normalize_chat_model_error(exc)
        raise BrainPipelineError(msg) from exc

    reply = harness_out.reply
    model_used = harness_out.model_used
    harness_trace = harness_out.trace_dict()

    sid = session_id
    if user_id:
        from sensehub.db import sessions as session_repo

        if sid:
            sess = session_repo.get_session(sid)
            if not sess or str(sess.get("user_id")) != user_id:
                sid = session_repo.create_session(user_id=user_id, title=text[:28], channel="studio")
        else:
            sid = session_repo.create_session(user_id=user_id, title=text[:28], channel="studio")
        session_repo.append_message(sid, role="user", content=text)
        session_repo.append_message(sid, role="assistant", content=reply)
        session_repo.touch_session(sid, title=text[:28])

    log_audit(
        input_text=text,
        action="studio_chat",
        result=f"{model_used} | {reply[:180]}",
    )
    return {
        "action": "answer",
        "reply": reply,
        "session_id": sid or session_id,
        "model_id": selected_id or None,
        "model_used": model_used or None,
        "harness_trace": harness_trace,
    }


async def process_code_assist(
    user_text: str,
    *,
    project_root: str = "",
    project_files: list[str] | None = None,
    file_path: str = "",
    file_content: str = "",
    context_files: list[dict[str, str]] | None = None,
    history: list[dict[str, Any]] | None = None,
    model_id: str = "",
    mode: str = "agent",
) -> dict[str, Any]:
    """Code Agent：Code Harness 编排后生成文件修改."""
    raw = user_text.strip()
    if not raw:
        raise BrainPipelineError("内容不能为空")

    text = normalize_user_text(raw)
    hist = _history_payload(history)
    harness_mode = mode if mode in ("agent", "plan") else "agent"
    try:
        out = await run_code_harness(
            text,
            project_root=project_root,
            project_files=project_files,
            file_path=file_path,
            file_content=file_content,
            context_files=context_files,
            history=hist,
            model_id=model_id,
            mode=harness_mode,
        )
    except Exception as exc:
        raise BrainPipelineError(f"Code 助手不可用: {exc}") from exc

    log_audit(input_text=text, action="code_assist", result=out.reply[:200])
    return {
        "action": "answer",
        "reply": out.reply,
        "edits": out.edits,
        "harness_trace": out.trace_dict(),
        "model_id": model_id or None,
        "mode": harness_mode,
    }


async def process_user_input(
    user_text: str,
    *,
    source: str = "text",
    history: list[dict[str, Any]] | None = None,
    session_id: str = "",
    user_id: str = "",
) -> dict[str, Any]:
    """唯一分流入口：意图脑 → Console Harness → Gateway AgentRuntime."""
    from sensehub.runtime.request_context import set_llm_usage_user

    if user_id:
        set_llm_usage_user(user_id)
    raw = user_text.strip()
    if not raw:
        raise BrainPipelineError("内容不能为空")

    text = normalize_user_text(raw)
    agents: list[dict[str, Any]] = []
    hist = _history_payload(history)

    from sensehub.gateway import events as agent_events

    sid = session_id or ""
    agent_events.emit({"type": "phase", "session_id": sid, "phase": "intent", "status": "running"})

    atomic_plan = match_atomic_plan(text)
    if atomic_plan:
        agent_events.emit({"type": "phase", "session_id": sid, "phase": "intent", "status": "done", "goal": atomic_plan.summary})
        from sensehub.gateway.agent_service import run_plan_agent

        intent_raw = {
            "action_mode": "execute",
            "user_wants": "desktop_action",
            "goal": text[:120],
            "suggested_tools": [s.tool for s in atomic_plan.steps],
            "_session_id": session_id,
        }
        agents.append({"role": "atomic_plan", "summary": atomic_plan.summary, "steps": len(atomic_plan.steps)})
        loop_out = await run_plan_agent(
            atomic_plan,
            text,
            session_id=session_id,
            user_id=user_id or "local",
            source=source,
            history=hist,
            intent_raw=intent_raw,
        )
        agents.extend(loop_out.get("agents") or [])
        if loop_out.get("needs_confirm"):
            msg = str(loop_out.get("answer") or atomic_plan.summary)
            return {
                "action": "execute",
                "matched": True,
                "plan": loop_out["plan"],
                "agents": agents,
                "intent_raw": intent_raw,
                "message": msg,
                "reply": msg,
            }
        _maybe_save_plan_cache(text, loop_out["plan"], intent_raw, loop_out.get("step_results") or [])
        return {
            "action": "execute",
            "matched": True,
            "executed": True,
            "plan": loop_out["plan"],
            "step_results": loop_out.get("step_results") or [],
            "reply": loop_out.get("answer", ""),
            "agents": agents,
            "intent_raw": intent_raw,
            "message": loop_out.get("answer", ""),
            "session_id": loop_out.get("session_id", session_id),
        }

    prefix = f"[{source}] " if source != "text" else ""
    hist_block = format_history_for_brain(hist)
    intent_user = f"{prefix}{text}"
    if hist_block:
        intent_user = f"{hist_block}\n\n当前用户消息：{intent_user}"
    try:
        router = LLMRouter()
        intent_raw = await router.chat_json("intent", INTENT_SYSTEM, intent_user)
    except Exception as exc:
        agent_events.emit({"type": "phase", "session_id": sid, "phase": "intent", "status": "error"})
        raise BrainPipelineError(f"意图脑不可用: {exc}") from exc

    agent_events.emit(
        {
            "type": "phase",
            "session_id": sid,
            "phase": "intent",
            "status": "done",
            "goal": str(intent_raw.get("goal") or text[:80]),
        }
    )

    agents.append({"role": "intent", "model_role": "intent", **intent_raw})
    intent_raw["_session_id"] = session_id
    log_audit(input_text=text, action="brain_intent", result=str(intent_raw.get("action_mode", "")))

    route = reconcile_route(intent_raw)
    if route.adjusted:
        agents.append(
            {
                "role": "harness",
                "from_mode": intent_raw.get("action_mode"),
                "to_mode": route.action_mode,
                "reason": route.reason,
            }
        )
    mode = route.action_mode
    intent_raw = {**intent_raw, "action_mode": mode, "user_wants": route.user_wants}

    if _is_pure_conversation(intent_raw):
        return await _answer_conversation(
            text,
            history=hist,
            session_id=str(intent_raw.get("_session_id") or session_id or ""),
            intent_raw=intent_raw,
            agents=agents,
        )

    try:
        from sensehub.gateway.agent_service import run_agent, run_plan_agent

        matched = match_quick_plan(text) if _quick_plan_enabled() and mode == "execute" else None
        quick_plan = matched
        if quick_plan:
            agents.append(
                {
                    "role": "quick_plan",
                    "summary": quick_plan.summary,
                    "steps": len(quick_plan.steps),
                }
            )
            loop_out = await run_plan_agent(
                quick_plan,
                text,
                session_id=str(intent_raw.get("_session_id") or session_id or ""),
                user_id=user_id or "local",
                source=source,
                history=hist,
                intent_raw=intent_raw,
            )
        else:
            loop_out = await run_agent(
                text,
                session_id=str(intent_raw.get("_session_id") or session_id or ""),
                user_id=user_id or "local",
                source=source,
                history=hist,
                intent_raw=intent_raw,
            )
        agents.extend(loop_out.get("agents") or [])
        _append_safety_agent(agents, loop_out["plan"])

        if loop_out.get("needs_confirm"):
            msg = str(loop_out.get("answer") or loop_out["plan"].summary or "该操作需你确认后才会继续执行")
            return {
                "action": "execute",
                "matched": True,
                "plan": loop_out["plan"],
                "agents": agents,
                "intent_raw": intent_raw,
                "message": msg,
                "reply": msg,
            }

        response_action = mode if mode in ("answer", "status", "cancel") else "execute"
        if response_action == "execute":
            _maybe_save_plan_cache(text, loop_out["plan"], intent_raw, loop_out.get("step_results") or [])
        return {
            "action": response_action,
            "matched": True,
            "executed": True,
            "plan": loop_out["plan"],
            "step_results": loop_out.get("step_results") or [],
            "reply": loop_out.get("answer", ""),
            "agents": agents,
            "intent_raw": intent_raw,
            "message": loop_out.get("answer", ""),
            "session_id": loop_out.get("session_id", session_id),
        }
    except Exception as exc:
        return {
            "action": "error",
            "matched": False,
            "message": str(exc),
            "agents": agents,
        }
