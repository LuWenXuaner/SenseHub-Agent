"""编排 Harness（Console / Hub Agent 实现层）.

对外请使用 sensehub.cognition.console_harness；
Chat 用 chat_harness，Code 用 code_harness。三者职责分离，勿混用。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sensehub.execution.tools.catalog import TOOL_CATALOG, tool_returns_data
from sensehub.models.schemas import ExecutionPlan


class PlanDeliveryMismatch(Exception):
    """计划中的工具无法交付用户期望的结果（应由应答脑处理）."""

    def __init__(self, message: str, *, agents: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.agents = agents or []


@dataclass(frozen=True)
class ResolvedRoute:
    action_mode: str
    user_wants: str
    adjusted: bool
    reason: str = ""


_BROWSER_SIDE_EFFECT = frozenset({"web_search", "open_url"})


def _normalize_mode(value: str) -> str:
    mode = str(value or "").lower().strip()
    return mode if mode in {"answer", "execute", "status", "cancel"} else "execute"


def _normalize_user_wants(value: str, *, action_mode: str, intent_type: str) -> str:
    wants = str(value or "").lower().strip()
    if wants in {"text_answer", "desktop_action", "both"}:
        return wants
    if action_mode == "answer" or intent_type in {"query", "chat"}:
        return "text_answer"
    if action_mode in {"status", "cancel"}:
        return "text_answer"
    return "desktop_action"


def reconcile_route(intent_raw: dict[str, Any]) -> ResolvedRoute:
    """根据意图脑 JSON 契约解析路由；仅在结构化字段矛盾时做确定性修正（非关键词表）."""
    mode = _normalize_mode(intent_raw.get("action_mode"))
    intent_type = str(intent_raw.get("intent_type", "")).lower()
    user_wants = _normalize_user_wants(
        str(intent_raw.get("user_wants", "")),
        action_mode=mode,
        intent_type=intent_type,
    )
    adjusted = False
    reason = ""

    if user_wants == "text_answer" and mode == "execute":
        mode = "answer"
        adjusted = True
        reason = "user_wants=text_answer 与 action_mode=execute 矛盾，改走应答链"
    elif user_wants == "desktop_action" and mode == "answer":
        mode = "execute"
        adjusted = True
        reason = "user_wants=desktop_action 与 action_mode=answer 矛盾，改走执行链"
    elif mode == "status":
        user_wants = "text_answer"
    elif mode == "cancel":
        user_wants = "text_answer"

    return ResolvedRoute(action_mode=mode, user_wants=user_wants, adjusted=adjusted, reason=reason)


def apply_sandbox_confirm_gates(plan: ExecutionPlan) -> ExecutionPlan:
    """工作区外文件写入自动升级为 L2 待确认（通用沙箱，非个案规则）."""
    from sensehub.security.sandbox import path_needs_confirm

    write_tools = {"write_file", "copy_file"}
    steps = []
    changed = False
    for step in plan.steps:
        if step.tool in write_tools:
            path_key = "path" if step.tool == "write_file" else "dst"
            target = str(step.params.get(path_key, ""))
            if target and path_needs_confirm(target, "write"):
                if step.risk_level != "L2" or not step.requires_confirm:
                    changed = True
                steps.append(
                    step.model_copy(
                        update={
                            "risk_level": "L2",
                            "requires_confirm": True,
                            "description": step.description
                            or f"写入沙箱外路径（需你确认）：{target}",
                        }
                    )
                )
                continue
        steps.append(step)
    if not changed:
        return plan
    return plan.model_copy(update={"steps": steps})


def validate_plan_delivery(intent_raw: dict[str, Any], plan: ExecutionPlan) -> None:
    """执行前校验：工具能力是否匹配用户期望（Harness 核心不变量）."""
    route = reconcile_route(intent_raw)
    if route.user_wants == "desktop_action":
        return
    if not plan.steps:
        return

    tools = [s.tool for s in plan.steps]
    if route.user_wants in {"text_answer", "both"}:
        has_data = any(tool_returns_data(t) for t in tools)
        only_browser_side_effect = tools and all(t in _BROWSER_SIDE_EFFECT for t in tools)
        if only_browser_side_effect and not has_data:
            raise PlanDeliveryMismatch(
                "计划仅打开浏览器/搜索页，无法向用户交付文字答案；应由应答脑直接回答",
            )
        if route.user_wants == "text_answer" and not has_data:
            side_effect_tools = [t for t in tools if not tool_returns_data(t)]
            if side_effect_tools and len(side_effect_tools) == len(tools):
                raise PlanDeliveryMismatch(
                    f"计划工具 {side_effect_tools} 均为副作用操作，无法生成用户要的文字结果",
                )


def describe_tool_outcome(tool: str) -> str:
    meta = TOOL_CATALOG.get(tool, {})
    if meta.get("returns_data"):
        return "返回数据，可供应答脑引用"
    side = meta.get("side_effect") or "执行操作，不返回可供回答的正文内容"
    return str(side)
