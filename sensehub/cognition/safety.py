"""安全审查：多维评分 + 拦截危险计划."""

from __future__ import annotations

from sensehub.execution.tools.registry import REGISTRY
from sensehub.models.schemas import ExecutionPlan, SafetyScore

FORBIDDEN_TOOLS = {"run_shell", "format_disk", "modify_registry", "delete_file"}

_RISK_WEIGHT = {"L0": 8, "L1": 18, "L2": 42, "L3": 95}
_HEAVY_TOOLS = frozenset(
    {
        "browser_navigate",
        "browser_act",
        "browser_snapshot",
        "gui_agent",
        "generate_document",
        "run_document_script",
        "playwright",
    }
)
_IM_TOOLS = frozenset({"wechat_send_message", "qq_send_message"})

# 综合分阈值：operation/resource 越低越好，compliance 越高越好
_MAX_OPERATION_RISK = 84
_MAX_RESOURCE_COST = 88
_MIN_COMPLIANCE = 35


def _tool_risk(tool: str) -> str:
    entry = REGISTRY.get(tool)
    return entry[1] if entry else "L1"


class SafetyReviewer:
    def score(self, plan: ExecutionPlan) -> SafetyScore:
        op = 0
        resource = 0
        compliance = 100
        flags: list[str] = []

        for step in plan.steps:
            tool = step.tool
            level = step.risk_level or _tool_risk(tool)
            op = max(op, _RISK_WEIGHT.get(level, 18))
            op += _RISK_WEIGHT.get(level, 18) // max(len(plan.steps), 1)

            if tool in FORBIDDEN_TOOLS or level == "L3":
                return SafetyScore(
                    operation_risk=100,
                    compliance=0,
                    resource_cost=100,
                    overall=0,
                    passed=False,
                    reason=f"步骤 {step.step_id} 被安全策略拒绝: {tool}",
                    flags=["forbidden_tool"],
                )

            if step.requires_confirm or level == "L2":
                flags.append("has_l2")
                compliance -= 12

            if tool in _HEAVY_TOOLS:
                resource += 22
                flags.append("heavy_tool")
            elif tool in _IM_TOOLS:
                resource += 12
                compliance -= 8
                flags.append("im_tool")
            else:
                resource += 6

        step_count = len(plan.steps)
        if step_count > 6:
            resource += (step_count - 6) * 5
            compliance -= 10
            flags.append("long_plan")
        if step_count > 10:
            compliance -= 15
            flags.append("very_long_plan")

        op = min(100, op)
        resource = min(100, resource)
        compliance = max(0, min(100, compliance))
        overall = max(
            0,
            min(100, int(compliance * 0.45 + (100 - op) * 0.35 + (100 - resource) * 0.2)),
        )

        passed = (
            op <= _MAX_OPERATION_RISK
            and resource <= _MAX_RESOURCE_COST
            and compliance >= _MIN_COMPLIANCE
        )
        reason = "ok"
        if not passed:
            hints: list[str] = []
            if op > _MAX_OPERATION_RISK:
                hints.append("操作风险偏高")
            if resource > _MAX_RESOURCE_COST:
                hints.append("资源消耗偏大")
            if compliance < _MIN_COMPLIANCE:
                hints.append("合规评分不足")
            reason = "；".join(hints) or "未通过安全审查"

        return SafetyScore(
            operation_risk=op,
            compliance=compliance,
            resource_cost=resource,
            overall=overall,
            passed=passed,
            reason=reason,
            flags=sorted(set(flags)),
        )

    def review(self, plan: ExecutionPlan) -> tuple[bool, str]:
        s = self.score(plan)
        return s.passed, s.reason if not s.passed else "ok"
