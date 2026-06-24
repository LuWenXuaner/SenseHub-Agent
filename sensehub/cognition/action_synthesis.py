"""执行前内容合成：取证工具 output → LLM 填写 action 工具正文参数（通用，非场景补丁）."""

from __future__ import annotations

import json
import re
from typing import Any

from sensehub.cognition.prompts import ACTION_SYNTHESIS_SYSTEM
from sensehub.cognition.router import LLMRouter
from sensehub.execution.tools.catalog import tool_returns_data
from sensehub.models.schemas import PlanStep, StepResult

# 需要「完整正文」的工具及其参数字段名
CONTENT_FIELD_BY_TOOL: dict[str, str] = {
    "notepad_type_save": "text",
    "type_text": "text",
    "write_file": "content",
    "generate_document": "content",
    "set_clipboard": "text",
}

_META_PLACEHOLDER_HINTS = (
    "待根据",
    "待生成",
    "稍后",
    "待定",
    "待补充",
    "待写入",
    "根据天气生成",
    "placeholder",
    "tbd",
)


def gather_evidence(steps: list[PlanStep], step_results: list[StepResult]) -> list[dict[str, Any]]:
    """本 run 内已成功取证（returns_data）的步骤输出."""
    by_id = {r.step_id: r for r in step_results}
    evidence: list[dict[str, Any]] = []
    for step in steps:
        result = by_id.get(step.step_id)
        if not result or not result.success:
            continue
        if not tool_returns_data(step.tool):
            continue
        out = result.output if isinstance(result.output, dict) else {}
        evidence.append({"tool": step.tool, "description": step.description, "output": out})
    return evidence


def _field_value(params: dict[str, Any], field: str) -> str:
    return str(params.get(field) or "").strip()


def _looks_like_placeholder(text: str) -> bool:
    low = text.strip().lower()
    if not low:
        return True
    if any(h.lower() in low for h in _META_PLACEHOLDER_HINTS):
        return True
    if len(low) < 24 and ("生成" in low or "安排" in low or "详细" in low):
        return True
    return False


def _looks_like_meta_instruction(text: str, evidence: list[dict[str, Any]] | None = None) -> bool:
    """正文参数像在对系统下指令，而非可交付给用户的成品."""
    t = text.strip()
    if not t:
        return False
    markers = (
        "执行时",
        "自动合成",
        "将根据",
        "根据 get_",
        "的 output",
        "的输出",
        "取证结果",
        "工具返回",
        "执行脑",
        "合成脑",
        "稍后写入",
        "随后再",
        "之后再",
        "intent",
        "tool_params",
    )
    if any(m in t or m.lower() in t.lower() for m in markers):
        return True
    if re.search(r"\boutput\b", t, re.I):
        return True
    for ev in evidence or []:
        name = str(ev.get("tool") or "")
        if name and name in t:
            return True
    return False


def _is_deliverable_body(text: str, evidence: list[dict[str, Any]] | None = None) -> bool:
    if _looks_like_placeholder(text) or _looks_like_meta_instruction(text, evidence):
        return False
    return len(text.strip()) >= 20


def needs_content_synthesis(
    tool: str,
    params: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> bool:
    """已有取证结果且正文缺失/非成品时，须走 LLM 合成."""
    field = CONTENT_FIELD_BY_TOOL.get(tool)
    if not field or not evidence:
        return False
    text = _field_value(params, field)
    if not text:
        return True
    return not _is_deliverable_body(text, evidence)


def post_gather_hint(user_text: str, gathered_tool: str, intent_raw: dict[str, Any] | None) -> str | None:
    """取证成功后给执行脑的通用提示（非天气专用）."""
    if not tool_returns_data(gathered_tool):
        return None
    wants_write = any(
        k in user_text for k in ("写入", "保存", "记事本", "文件", "粘贴", "键入", "输入")
    )
    wants_both = str((intent_raw or {}).get("user_wants") or "") == "both"
    if not wants_write and not wants_both:
        return None
    return (
        f"取证工具「{gathered_tool}」已完成。请根据返回的 output 用你自己的话写出完整、可交付的正文，"
        f"再调用 notepad_type_save / type_text / write_file 等（正文参数不可为空、不可写占位语）。"
    )


async def synthesize_tool_params(
    user_text: str,
    intent_raw: dict[str, Any] | None,
    target_tool: str,
    partial_params: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """调用合成脑，为 action 工具补全正文类参数."""
    field = CONTENT_FIELD_BY_TOOL.get(target_tool)
    if not field:
        return partial_params

    payload = {
        "user_goal": user_text,
        "intent": intent_raw or {},
        "target_tool": target_tool,
        "content_field": field,
        "partial_params": partial_params,
        "evidence": evidence,
    }
    user = json.dumps(payload, ensure_ascii=False)
    router = LLMRouter()
    raw = await router.chat_json("planner", ACTION_SYNTHESIS_SYSTEM, user)
    params_out = raw.get("params") if isinstance(raw.get("params"), dict) else raw
    if not isinstance(params_out, dict):
        raise RuntimeError("合成脑未返回 params 对象")

    merged = {**partial_params, **params_out}
    final = _field_value(merged, field)
    if not final:
        raise RuntimeError(f"合成脑未生成有效的 {field}")
    if not _is_deliverable_body(final, evidence):
        raise RuntimeError(f"合成脑返回的 {field} 仍非可交付正文，请重试")
    return merged
