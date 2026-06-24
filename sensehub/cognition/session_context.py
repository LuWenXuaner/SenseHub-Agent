"""多轮对话上下文：供意图脑 / 应答脑理解追问（如「刚才保存在哪」）."""

from __future__ import annotations

import json
from typing import Any

_MAX_TURNS = 10
_MAX_CHARS = 6000


def _compact_step(step: dict[str, Any], result: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "tool": step.get("tool"),
        "description": step.get("description"),
        "params": step.get("params") or {},
    }
    if result:
        out["success"] = result.get("success")
        if result.get("output"):
            out["output"] = result.get("output")
        if result.get("error"):
            out["error"] = result.get("error")
    return out


def compact_task_snapshot(task: dict[str, Any] | None) -> dict[str, Any] | None:
    if not task or not isinstance(task, dict):
        return None
    steps = task.get("plan_steps") or []
    results = {r.get("step_id"): r for r in (task.get("step_results") or []) if isinstance(r, dict)}
    compact_steps = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        sid = step.get("step_id")
        compact_steps.append(_compact_step(step, results.get(sid)))
    return {
        "task_id": task.get("task_id"),
        "intent_text": task.get("intent_text"),
        "summary": task.get("summary"),
        "status": task.get("status"),
        "steps": compact_steps,
    }


def format_history_for_brain(history: list[dict[str, Any]] | None, *, max_turns: int = _MAX_TURNS) -> str:
    if not history:
        return ""
    lines = ["### 近期对话（含上轮任务执行结果，用于理解追问）"]
    total = 0
    for turn in history[-max_turns:]:
        role = str(turn.get("role", "user")).lower()
        label = "用户" if role == "user" else "助手"
        content = str(turn.get("content", "")).strip()
        if not content:
            continue
        block = f"{label}：{content}"
        task = compact_task_snapshot(turn.get("task"))
        if task:
            block += f"\n  [上轮任务] {json.dumps(task, ensure_ascii=False)}"
        if total + len(block) > _MAX_CHARS:
            break
        lines.append(block)
        total += len(block)
    if len(lines) <= 1:
        return ""
    return "\n".join(lines)


def artifacts_from_task(task: dict[str, Any] | None) -> list[str]:
    """从任务结果提取路径等可引用产物（供兜底答复）."""
    if not task:
        return []
    found: list[str] = []
    for result in task.get("step_results") or []:
        if not isinstance(result, dict) or not result.get("success"):
            continue
        output = result.get("output") or {}
        if not isinstance(output, dict):
            continue
        for key in ("path", "dst", "src", "screenshot_path", "opened"):
            val = output.get(key)
            if val and str(val) not in found:
                found.append(str(val))
    return found


def fallback_reply_from_task(plan: Any, task: Any) -> str:
    """应答脑不可用时的确定性汇总（仅依据 step output，不做工具名特判）."""
    task_dict = task.model_dump() if hasattr(task, "model_dump") else dict(task or {})
    paths = artifacts_from_task(task_dict)
    if paths:
        return f"已完成。相关路径：{'；'.join(paths)}"
    summary = str(task_dict.get("summary") or "").strip()
    if summary and not _is_internal_summary(summary):
        return summary
    return "任务已完成。"


def _is_internal_summary(text: str) -> bool:
    import re

    return bool(re.search(r"意图:|规划:\d+步|执行:\d+步", text))
