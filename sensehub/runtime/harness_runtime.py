"""运行时 Harness：UI 门禁、IM 搜索规程、登录界面拦截、安全审查."""

from __future__ import annotations

import re
from typing import Any

from sensehub.cognition.harness import apply_sandbox_confirm_gates
from sensehub.cognition.safety import SafetyReviewer
from sensehub.execution.tools.desktop import is_login_title
from sensehub.models.schemas import ExecutionPlan, PlanStep, StepResult
from sensehub.runtime.verifier import ui_verified

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
        "gui_agent",
    }
)
_OBSERVE_TOOLS = frozenset({"open_app", "focus_window", "active_window", "list_windows", "screenshot"})
_SEARCH_TOOLS = frozenset({"hotkey", "gui_agent", "browser_snapshot", "browser_act"})
_IM_GOAL_HINTS = re.compile(
    r"好友|联系人|会话|聊天|发消息|对话框|找.*人|搜索.*(?:好友|联系人)|微信|wechat|qq|钉钉|飞书",
    re.I,
)
_IM_APP_HINTS = re.compile(
    r"微信|wechat|qq|钉钉|dingtalk|飞书|feishu|企业微信|telegram|discord|slack",
    re.I,
)

_LOGIN_BLOCK_MSG = (
    "检测到应用处于登录/扫码界面。我们不会代替您输入账号密码或扫码登录。"
    "请先在本地手动完成登录，然后重新发起指令（例如「我已登录，请继续搜索好友」），我再继续后续操作。"
)


def needs_im_search_flow(user_text: str, intent_raw: dict[str, Any] | None) -> bool:
    blob = user_text
    if intent_raw:
        blob += " " + str(intent_raw.get("goal", ""))
    return bool(_IM_GOAL_HINTS.search(blob))


def targets_im_app(user_text: str, intent_raw: dict[str, Any] | None, tool_output: dict[str, Any] | None) -> bool:
    blob = user_text
    if intent_raw:
        blob += " " + str(intent_raw.get("goal", ""))
    if tool_output:
        blob += " " + str(tool_output.get("opened", "")) + " " + str(tool_output.get("focused", ""))
    return bool(_IM_APP_HINTS.search(blob))


def im_search_done(prior_steps: list[PlanStep]) -> bool:
    if any(s.tool == "wechat_send_message" for s in prior_steps):
        return True
    return any(s.tool in _SEARCH_TOOLS for s in prior_steps)


def _title_from_output(tool: str, output: dict[str, Any]) -> str:
    if tool == "active_window":
        return str(output.get("title") or "")
    if tool in {"open_app", "focus_window"}:
        return str(output.get("focused_window") or "")
    if tool == "list_windows":
        windows = output.get("windows")
        if isinstance(windows, list) and windows:
            return str(windows[0])
    return ""


def gate_login_screen(
    tool: str,
    output: dict[str, Any] | None,
    user_text: str,
    intent_raw: dict[str, Any] | None,
) -> str | None:
    """观察类工具后：若 IM 类应用停在登录界面则拦截."""
    if tool not in _OBSERVE_TOOLS or not output:
        return None
    if not targets_im_app(user_text, intent_raw, output):
        return None

    if tool == "open_app":
        titles = output.get("matching_windows")
        if isinstance(titles, list) and titles:
            non_login = [t for t in titles if not is_login_title(str(t))]
            if not non_login and any(is_login_title(str(t)) for t in titles):
                return _LOGIN_BLOCK_MSG
        focused = str(output.get("focused_window") or "")
        if focused and is_login_title(focused):
            return _LOGIN_BLOCK_MSG
        return None

    title = _title_from_output(tool, output)
    if title and is_login_title(title):
        return _LOGIN_BLOCK_MSG
    return None


def gate_ui_action(step: PlanStep, prior_steps: list[PlanStep], user_text: str, intent_raw: dict | None) -> str | None:
    if step.tool in {"notepad_type_save", "wechat_send_message"}:
        return None
    if step.tool in _UI_ACTION_TOOLS and not ui_verified(prior_steps):
        return (
            "须先 open_app / focus_window 置前目标应用，再 type_text / save_notepad / hotkey。"
            "open_app 之后默认已聚焦，直接后续操作即可。"
        )
    if (
        step.tool == "type_text"
        and needs_im_search_flow(user_text, intent_raw)
        and not im_search_done(prior_steps)
    ):
        params_text = str(step.params.get("text", ""))
        if params_text and len(params_text) <= 32:
            return (
                "在 IM/聊天应用内查找联系人须先打开搜索：微信 hotkey(app=微信, keys=[ctrl,f])；"
                "或 wechat_send_message 一步完成。"
                "再 type_text 输入姓名 → Enter 进入会话。"
                "确认进入正确会话后再输入消息。若应用未登录，请先告知用户自行登录。"
            )
    return None


def review_plan_safety(plan: ExecutionPlan) -> tuple[bool, str]:
    safe, reason = SafetyReviewer().review(plan)
    return safe, reason


__all__ = [
    "apply_sandbox_confirm_gates",
    "gate_login_screen",
    "gate_ui_action",
    "needs_im_search_flow",
    "review_plan_safety",
]
