"""多脑协作：意图 → 规划 → 安全审查 → Harness 校验."""

from __future__ import annotations

import json
from typing import Any

from sensehub.cognition.harness import PlanDeliveryMismatch, apply_sandbox_confirm_gates, validate_plan_delivery
from sensehub.cognition.planner import Planner
from sensehub.cognition.prompts import INTENT_SYSTEM
from sensehub.cognition.router import LLMRouter
from sensehub.cognition.safety import SafetyReviewer
from sensehub.models.schemas import ExecutionPlan


class BrainPipelineError(Exception):
    def __init__(self, message: str, *, agents: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.agents = agents or []


async def orchestrate_brains(
    user_text: str,
    *,
    intent_raw: dict[str, Any] | None = None,
    planner_input: str | None = None,
) -> tuple[ExecutionPlan, list[dict[str, Any]]]:
    """意图脑 + 规划脑 + 安全脑 + Harness 交付校验."""
    text = user_text.strip()
    if not text:
        raise BrainPipelineError("指令不能为空")

    router = LLMRouter()
    agents: list[dict[str, Any]] = []

    if intent_raw is None:
        intent_raw = await router.chat_json("intent", INTENT_SYSTEM, text)
    agents.append({"role": "intent", "model_role": "intent", **intent_raw})

    if planner_input is None:
        planner_input = (
            f"用户指令：{text}\n\n"
            f"意图脑分析：{json.dumps(intent_raw, ensure_ascii=False)}"
        )
    planner = Planner()
    plan = await planner.plan_from_context(planner_input, original_intent=text)
    plan = apply_sandbox_confirm_gates(plan)
    agents.append(
        {
            "role": "planner",
            "model_role": "planner",
            "summary": plan.summary,
            "steps": [s.model_dump() for s in plan.steps],
        }
    )

    if not plan.steps:
        agents.append(
            {
                "role": "harness",
                "passed": False,
                "reason": "规划脑返回空步骤，应由应答脑直接回答",
                "action": "reroute_answer",
            }
        )
        raise BrainPipelineError("规划脑返回空步骤", agents=agents)

    safe, reason = SafetyReviewer().review(plan)
    agents.append({"role": "safety", "model_role": "safety", "passed": safe, "reason": reason})
    if not safe:
        raise BrainPipelineError(reason, agents=agents)

    try:
        validate_plan_delivery(intent_raw, plan)
    except PlanDeliveryMismatch as exc:
        agents.append(
            {
                "role": "harness",
                "passed": False,
                "reason": str(exc),
                "action": "reroute_answer",
            }
        )
        raise BrainPipelineError(str(exc), agents=agents) from exc

    agents.append({"role": "harness", "passed": True, "reason": "工具能力与用户期望一致"})
    return plan, agents


def format_brain_summary(agents: list[dict[str, Any]]) -> str:
    parts = []
    for a in agents:
        role = a.get("role", "?")
        if role == "intent":
            parts.append(f"意图:{a.get('goal', '')[:40]}")
        elif role == "planner":
            parts.append(f"规划:{len(a.get('steps', []))}步")
        elif role == "safety":
            parts.append("安全:通过" if a.get("passed") else "安全:拒绝")
        elif role == "harness":
            parts.append("校验:通过" if a.get("passed") else "校验:改应答")
        elif role == "executor":
            parts.append(f"执行:{a.get('steps_done', 0)}步")
    return " · ".join(parts) if parts else "多脑协作"
