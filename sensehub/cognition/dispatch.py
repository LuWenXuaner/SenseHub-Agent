"""用户输入唯一入口：意图脑 → Harness 路由 → Gateway AgentRuntime（OpenClaw 单循环）."""

from __future__ import annotations

import json
import re
from typing import Any

from sensehub.cognition.brain import BrainPipelineError
from sensehub.cognition.harness import reconcile_route
from sensehub.cognition.prompts import ANSWER_SYSTEM, CODE_ASSIST_SYSTEM, INTENT_SYSTEM
from sensehub.cognition.router import LLMRouter
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
    out = list(agents or [])
    for step in plan.steps:
        result = next((r for r in task.step_results if r.step_id == step.step_id), None)
        out.append(
            {
                "role": "executor",
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


async def synthesize_task_reply(
    user_text: str,
    plan: ExecutionPlan,
    task: TaskResponse,
    *,
    agents: list[dict[str, Any]] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> str:
    """多步执行完成后，由应答脑汇总成用户可读最终结果."""
    if task.status == "failed":
        return task.error or "任务执行失败，请稍后重试"
    router = LLMRouter()
    step_payload = []
    for step in plan.steps:
        result = next((r for r in task.step_results if r.step_id == step.step_id), None)
        step_payload.append(
            {
                "tool": step.tool,
                "description": step.description,
                "success": result.success if result else False,
                "output": result.output if result else {},
                "error": result.error if result else None,
            }
        )
    hist_block = format_history_for_brain(_history_payload(history))
    parts = [
        *( [hist_block] if hist_block else [] ),
        f"用户原话：{user_text}",
        f"计划摘要：{plan.summary}",
        f"各步结果：{json.dumps(step_payload, ensure_ascii=False)}",
    ]
    try:
        reply = await router.chat(
            "intent",
            [
                {"role": "system", "content": ANSWER_SYSTEM},
                {"role": "user", "content": "\n\n".join(parts)},
            ],
            temperature=0.4,
            max_tokens=1024,
        )
    except Exception:
        reply = fallback_reply_from_task(plan, task)
    if not reply.strip():
        reply = fallback_reply_from_task(plan, task)
    if agents is not None:
        agents.append({"role": "answer", "model_role": "intent", "preview": reply[:80]})
    return reply


async def process_studio_chat(
    user_text: str,
    *,
    history: list[dict[str, Any]] | None = None,
    session_id: str = "",
) -> dict[str, Any]:
    """Studio 纯对话：仅应答，不触发桌面/浏览器执行."""
    raw = user_text.strip()
    if not raw:
        raise BrainPipelineError("内容不能为空")

    text = normalize_user_text(raw)
    hist = _history_payload(history)
    router = LLMRouter()
    hist_block = format_history_for_brain(hist)
    user_content = text if not hist_block else f"{hist_block}\n\n当前用户消息：{text}"
    messages = [
        {"role": "system", "content": ANSWER_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    try:
        reply = await router.chat("intent", messages, temperature=0.5, max_tokens=2048)
    except Exception as exc:
        raise BrainPipelineError(f"对话不可用: {exc}") from exc

    sid = session_id
    if sid:
        from sensehub.db import sessions as session_repo

        if not session_repo.get_session(sid):
            sid = session_repo.create_session(title=text[:28], channel="studio")
        session_repo.append_message(sid, role="user", content=text)
        session_repo.append_message(sid, role="assistant", content=reply)
        session_repo.touch_session(sid, title=text[:28])

    log_audit(input_text=text, action="studio_chat", result=reply[:200])
    return {"action": "answer", "reply": reply, "session_id": sid or session_id}


async def process_code_assist(
    user_text: str,
    *,
    project_root: str = "",
    project_files: list[str] | None = None,
    file_path: str = "",
    file_content: str = "",
    context_files: list[dict[str, str]] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Code Agent：根据项目上下文生成文件修改（由浏览器写回本地）."""
    raw = user_text.strip()
    if not raw:
        raise BrainPipelineError("内容不能为空")

    text = normalize_user_text(raw)
    hist = _history_payload(history)
    router = LLMRouter()
    hist_block = format_history_for_brain(hist)

    blocks: list[str] = []
    if project_root:
        blocks.append(f"项目根目录：{project_root}")
    files = project_files or []
    if files:
        listing = "\n".join(f"- {p}" for p in files[:120])
        blocks.append(f"项目文件列表（共 {len(files)} 个）：\n{listing}")
    if file_path and file_content is not None:
        blocks.append(f"当前聚焦文件：{file_path}\n```\n{file_content}\n```")
    for item in context_files or []:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        content = str(item.get("content") or "")
        if path and path != file_path:
            blocks.append(f"附加上下文文件：{path}\n```\n{content[:12000]}\n```")

    user_content = text
    if blocks:
        user_content = "\n\n".join(blocks) + f"\n\n用户指令：{text}"
    if hist_block:
        user_content = f"{hist_block}\n\n{user_content}"

    try:
        result = await router.chat_json("intent", CODE_ASSIST_SYSTEM, user_content)
    except Exception as exc:
        raise BrainPipelineError(f"Code 助手不可用: {exc}") from exc

    reply = str(result.get("reply") or "").strip()
    edits_raw = result.get("edits")
    edits: list[dict[str, str]] = []
    if isinstance(edits_raw, list):
        for item in edits_raw:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip()
            content = str(item.get("content") or "")
            if path:
                edits.append({"path": path, "content": content})

    if not reply:
        reply = "已完成分析。" if edits else "未生成文件修改。"

    log_audit(input_text=text, action="code_assist", result=reply[:200])
    return {"action": "answer", "reply": reply, "edits": edits}


async def process_user_input(
    user_text: str,
    *,
    source: str = "text",
    history: list[dict[str, Any]] | None = None,
    session_id: str = "",
) -> dict[str, Any]:
    """唯一分流入口：意图脑 → Harness → Gateway AgentRuntime（问答与执行同一 FC 循环）."""
    raw = user_text.strip()
    if not raw:
        raise BrainPipelineError("内容不能为空")

    text = normalize_user_text(raw)
    agents: list[dict[str, Any]] = []
    hist = _history_payload(history)

    prefix = f"[{source}] " if source != "text" else ""
    hist_block = format_history_for_brain(hist)
    intent_user = f"{prefix}{text}"
    if hist_block:
        intent_user = f"{hist_block}\n\n当前用户消息：{intent_user}"
    try:
        router = LLMRouter()
        intent_raw = await router.chat_json("intent", INTENT_SYSTEM, intent_user)
    except Exception as exc:
        raise BrainPipelineError(f"意图脑不可用: {exc}") from exc

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

    try:
        from sensehub.gateway.agent_service import run_agent

        loop_out = await run_agent(
            text,
            session_id=str(intent_raw.get("_session_id") or ""),
            source=source,
            history=hist,
            intent_raw=intent_raw,
        )
        agents.extend(loop_out.get("agents") or [])

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
