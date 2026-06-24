"""原子桌面工具执行后的快速答复（免应答脑二次 LLM）."""

from __future__ import annotations

from sensehub.cognition.session_context import fallback_reply_from_steps
from sensehub.models.schemas import PlanStep, StepResult

_ATOMIC_TOOLS = frozenset({"wechat_send_message", "notepad_type_save"})


def should_fast_atomic_reply(steps: list[PlanStep], step_results: list[StepResult]) -> bool:
    if not steps or not step_results:
        return False
    if not all(r.success for r in step_results):
        return False
    tools = {s.tool for s in steps}
    return len(tools) == 1 and next(iter(tools)) in _ATOMIC_TOOLS


def fast_atomic_reply(
    steps: list[PlanStep],
    step_results: list[StepResult],
    *,
    plan_summary: str = "",
) -> str:
    tool = steps[0].tool if steps else ""
    result = step_results[0] if step_results else None
    out = (result.output or {}) if result else {}

    if tool == "wechat_send_message" and result and result.success:
        contact = str(out.get("contact") or "").strip()
        message = str(out.get("message") or "").strip()
        sent = bool(out.get("sent"))
        if contact and message:
            if sent:
                return f"已向「{contact}」发送「{message}」"
            return f"已在与「{contact}」的会话中输入「{message}」"
        if contact:
            return f"已打开与「{contact}」的微信会话"

    if tool == "notepad_type_save" and result and result.success:
        name = str(out.get("filename") or "").strip()
        if name:
            return f"已将内容写入记事本并保存为「{name}」"
        return "已将内容写入记事本并保存"

    return fallback_reply_from_steps(steps, step_results, plan_summary=plan_summary)
