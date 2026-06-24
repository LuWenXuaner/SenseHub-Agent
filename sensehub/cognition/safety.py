"""安全审查：拦截危险计划."""

from __future__ import annotations

from sensehub.models.schemas import ExecutionPlan

FORBIDDEN_TOOLS = {"run_shell", "format_disk", "modify_registry", "delete_file"}


class SafetyReviewer:
    def review(self, plan: ExecutionPlan) -> tuple[bool, str]:
        for step in plan.steps:
            if step.tool in FORBIDDEN_TOOLS or step.risk_level == "L3":
                return False, f"步骤 {step.step_id} 被安全策略拒绝: {step.tool}"
        return True, "ok"
