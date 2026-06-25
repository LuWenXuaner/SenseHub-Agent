"""原子桌面工具执行后的快速答复（免应答脑二次 LLM）."""

from __future__ import annotations

from sensehub.cognition.session_context import fallback_reply_from_steps
from sensehub.models.schemas import PlanStep, StepResult

_ATOMIC_TOOLS = frozenset(
    {"wechat_send_message", "notepad_type_save", "search_and_download_image", "generate_document", "run_document_script"}
)


def should_fast_atomic_reply(steps: list[PlanStep], step_results: list[StepResult]) -> bool:
    if not steps or not step_results:
        return False
    if not all(r.success for r in step_results):
        return False
    tools = {s.tool for s in steps}
    if len(tools) == 1 and next(iter(tools)) in _ATOMIC_TOOLS:
        return True
    # open_app 仅作前置时，微信/记事本仍走原子答复
    if "wechat_send_message" in tools and tools <= {"open_app", "wechat_send_message", "focus_window"}:
        return True
    if "search_and_download_image" in tools and tools <= {
        "search_and_download_image",
        "open_app",
        "focus_window",
        "web_search",
    }:
        return True
    if "notepad_type_save" in tools and tools <= {"open_app", "notepad_type_save", "focus_window"}:
        return True
    return False


def _atomic_step_result(
    steps: list[PlanStep], step_results: list[StepResult]
) -> tuple[str, PlanStep | None, StepResult | None]:
    by_id = {r.step_id: r for r in step_results}
    for step in reversed(steps):
        if step.tool not in _ATOMIC_TOOLS:
            continue
        result = by_id.get(step.step_id)
        if result and result.success:
            return step.tool, step, result
    return "", None, None


def fast_atomic_reply(
    steps: list[PlanStep],
    step_results: list[StepResult],
    *,
    plan_summary: str = "",
) -> str:
    tool, _step, result = _atomic_step_result(steps, step_results)
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
        path = str(out.get("saved_path") or "").strip()
        size = int(out.get("file_size") or 0)
        closed = bool(out.get("closed"))
        if size <= 0:
            return "记事本保存失败：文件内容为空"
        base = ""
        if name and path:
            base = f"已将内容写入记事本并保存为「{name}」（{path}）"
        elif name:
            base = f"已将内容写入记事本并保存为「{name}」"
        else:
            base = "已将内容写入记事本并保存"
        if closed:
            return f"{base}，并已关闭记事本"
        return base

    if tool == "search_and_download_image" and result and result.success:
        path = str(out.get("saved_path") or "").strip()
        query = str(out.get("query") or "").strip()
        if path and query:
            return f"已搜索「{query}」并下载图片到 {path}"
        if path:
            return f"图片已下载到 {path}"
        return "图片已下载"

    if tool == "generate_document" and result and result.success:
        path = str(out.get("path") or "").strip()
        fmt = str(out.get("format") or "文档").strip()
        if path:
            return f"已生成 {fmt} 文件：{path}"
        return "文档已生成"

    if tool == "run_document_script" and result and result.success:
        path = str(out.get("path") or "").strip()
        if path:
            return f"已通过 Python 脚本生成文件：{path}"
        return "脚本已执行并保存文件"

    return fallback_reply_from_steps(steps, step_results, plan_summary=plan_summary)
