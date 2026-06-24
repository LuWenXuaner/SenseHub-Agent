"""桌面任务事实验收（失败检测等；用户向回复由应答脑统一生成）."""

from __future__ import annotations

from sensehub.models.schemas import PlanStep, StepResult

_UI_VERIFY_TOOLS = frozenset(
    {"open_app", "focus_window", "list_windows", "active_window", "screenshot", "gui_agent"}
)
_UI_ACTION_TOOLS = frozenset(
    {
        "type_text",
        "save_notepad",
        "notepad_type_save",
        "wechat_send_message",
        "hotkey",
        "press_key",
        "click",
        "double_click",
        "scroll",
        "right_click",
    }
)


def ui_verified(prior_steps: list[PlanStep]) -> bool:
    return any(s.tool in _UI_VERIFY_TOOLS for s in prior_steps)


def is_desktop_run(intent_raw: dict | None, steps: list[PlanStep]) -> bool:
    if intent_raw and str(intent_raw.get("user_wants", "")) in {"desktop_action", "both"}:
        return True
    desktop_tools = _UI_VERIFY_TOOLS | _UI_ACTION_TOOLS
    return any(s.tool in desktop_tools for s in steps)


def target_apps_from_steps(steps: list[PlanStep]) -> list[str]:
    names: list[str] = []
    for step in steps:
        if step.tool == "open_app":
            name = str(step.params.get("name", "")).strip()
            if name:
                names.append(name)
        elif step.tool == "focus_window":
            name = str(step.params.get("title") or step.params.get("name") or "").strip()
            if name:
                names.append(name)
    return names


def collect_desktop_issues(steps: list[PlanStep], step_results: list[StepResult]) -> list[str]:
    """报告工具执行失败或明显未打开窗口等问题."""
    issues: list[str] = []
    step_by_id = {s.step_id: s for s in steps}

    for result in step_results:
        if not result.success:
            issues.append(f"第 {result.step_id} 步失败：{result.error or '未知错误'}")

    for result in step_results:
        step = step_by_id.get(result.step_id)
        if not step or not result.success:
            continue
        out = result.output or {}
        if step.tool == "open_app":
            count = int(out.get("window_count") or 0)
            if count < 1:
                issues.append(f"未找到应用「{out.get('opened')}」的窗口")

    return issues
