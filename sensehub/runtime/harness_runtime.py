"""运行时 Harness：UI 门禁、IM 搜索规程、安全审查."""

from __future__ import annotations

import re
from typing import Any

from sensehub.cognition.harness import apply_sandbox_confirm_gates
from sensehub.cognition.safety import SafetyReviewer
from sensehub.models.schemas import ExecutionPlan, PlanStep, StepResult
from sensehub.runtime.verifier import ui_verified

_UI_ACTION_TOOLS = frozenset(
    {"type_text", "hotkey", "press_key", "click", "double_click", "scroll", "right_click"}
)
_SEARCH_TOOLS = frozenset({"hotkey", "gui_agent", "browser_snapshot", "browser_act"})
_IM_GOAL_HINTS = re.compile(
    r"好友|联系人|会话|聊天|发消息|对话框|找.*人|搜索.*(?:好友|联系人)",
    re.I,
)


def needs_im_search_flow(user_text: str, intent_raw: dict[str, Any] | None) -> bool:
    blob = user_text
    if intent_raw:
        blob += " " + str(intent_raw.get("goal", ""))
    return bool(_IM_GOAL_HINTS.search(blob))


def im_search_done(prior_steps: list[PlanStep]) -> bool:
    return any(s.tool in _SEARCH_TOOLS for s in prior_steps)


def gate_ui_action(step: PlanStep, prior_steps: list[PlanStep], user_text: str, intent_raw: dict | None) -> str | None:
    if step.tool in _UI_ACTION_TOOLS and not ui_verified(prior_steps):
        return (
            "须先确认当前界面（list_windows、active_window、screenshot、"
            "open_app、focus_window 或 gui_agent）。对话历史不代表桌面仍停在上一轮状态。"
        )
    if (
        step.tool == "type_text"
        and needs_im_search_flow(user_text, intent_raw)
        and not im_search_done(prior_steps)
    ):
        params_text = str(step.params.get("text", ""))
        if params_text and len(params_text) <= 20:
            return (
                "在 IM/聊天应用内查找联系人须先 hotkey 搜索（如 Ctrl+F）或 gui_agent 定位，"
                "确认进入正确会话后再 type_text。"
            )
    return None


def review_plan_safety(plan: ExecutionPlan) -> tuple[bool, str]:
    safe, reason = SafetyReviewer().review(plan)
    return safe, reason


__all__ = [
    "apply_sandbox_confirm_gates",
    "gate_ui_action",
    "needs_im_search_flow",
    "review_plan_safety",
]
