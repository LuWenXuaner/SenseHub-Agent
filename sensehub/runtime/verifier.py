"""桌面任务事实验收（finish 时按工具结果生成答复）."""

from __future__ import annotations

from sensehub.execution.tools.desktop import window_matches_app
from sensehub.models.schemas import PlanStep, StepResult

_UI_VERIFY_TOOLS = frozenset(
    {"open_app", "focus_window", "list_windows", "active_window", "screenshot", "gui_agent"}
)
_UI_ACTION_TOOLS = frozenset(
    {"type_text", "hotkey", "press_key", "click", "double_click", "scroll", "right_click"}
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
            if out.get("launched") and count > 1:
                preview = "、".join((out.get("matching_windows") or [])[:3])
                issues.append(
                    f"启动「{out.get('opened')}」后出现 {count} 个匹配窗口"
                    f"（{preview}），可能存在重复实例或登录窗"
                )
        if step.tool == "type_text":
            fg = str(out.get("foreground_window") or "")
            app = str(step.params.get("app") or "").strip()
            targets = [app] if app else target_apps_from_steps(steps)
            for target in targets:
                if target and fg and not window_matches_app(fg, target):
                    issues.append(f"文字输入到了「{fg}」，与目标「{target}」不一致")
                    break

    return issues


def build_factual_desktop_answer(
    steps: list[PlanStep],
    step_results: list[StepResult],
    llm_answer: str,
) -> str:
    issues = collect_desktop_issues(steps, step_results)
    facts: list[str] = []
    step_by_id = {s.step_id: s for s in steps}

    for result in step_results:
        if not result.success:
            continue
        step = step_by_id.get(result.step_id)
        if not step:
            continue
        out = result.output or {}
        if step.tool == "open_app":
            if out.get("already_running"):
                facts.append(
                    f"「{out.get('opened')}」已在运行，已切换到「{out.get('focused_window') or '主窗口'}」"
                )
            elif out.get("launched"):
                count = out.get("window_count")
                suffix = f"（匹配窗口 {count} 个）" if count else ""
                focus = out.get("focused_window")
                facts.append(
                    f"已启动「{out.get('opened')}」{suffix}"
                    + (f"，聚焦「{focus}」" if focus else "")
                )
        elif step.tool == "type_text":
            text = str(out.get("text", ""))[:40]
            fg = out.get("foreground_window") or "未知窗口"
            facts.append(f"在「{fg}」输入「{text}」")
        elif step.tool == "active_window":
            facts.append(f"前台窗口：{out.get('title')}")
        elif step.tool == "hotkey":
            keys = step.params.get("keys") or step.params.get("key")
            if keys:
                facts.append(f"快捷键 {keys}")
        elif step.tool.startswith("browser_"):
            if out.get("url"):
                facts.append(f"浏览器：{out.get('url')}")

    if issues:
        issue_text = "；".join(issues)
        fact_text = "；".join(facts)
        if fact_text:
            return f"未能确认全部完成：{issue_text}。已执行：{fact_text}"
        return f"未能确认全部完成：{issue_text}"

    if facts:
        return "；".join(facts)
    return llm_answer
