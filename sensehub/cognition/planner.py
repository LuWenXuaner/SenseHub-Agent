"""任务规划：自然语言 → 结构化步骤（仅由 LLM 规划脑决策）."""

from __future__ import annotations

import uuid

from sensehub.cognition.quick_match import normalize_intent
from sensehub.cognition.prompts import PLANNER_SYSTEM
from sensehub.cognition.router import LLMRouter
from sensehub.models.schemas import ExecutionPlan, PlanStep


class Planner:
    def __init__(self) -> None:
        self.router = LLMRouter()

    async def plan_from_context(self, planner_input: str, *, original_intent: str = "") -> ExecutionPlan:
        data = await self.router.chat_json("planner", PLANNER_SYSTEM, planner_input)
        steps = [PlanStep(**s) for s in data.get("steps", [])]
        return ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            steps=steps,
            summary=data.get("summary", original_intent or planner_input[:80]),
        )

    async def plan(self, user_text: str) -> ExecutionPlan:
        normalized = normalize_intent(user_text)
        return await self.plan_from_context(f"用户指令：{normalized}", original_intent=normalized)
