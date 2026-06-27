"""成功规划模板缓存."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sensehub.cognition.quick_match import normalize_intent
from sensehub.db import plan_templates as tpl_repo
from sensehub.models.schemas import ExecutionPlan, PlanStep


def _intent_fingerprint(text: str, intent_raw: dict[str, Any] | None) -> str:
    norm = normalize_intent(text.strip())
    goal = ""
    wants = ""
    if intent_raw:
        goal = str(intent_raw.get("goal") or "").strip()[:120]
        wants = str(intent_raw.get("user_wants") or "").strip()
    blob = f"{norm}|{goal}|{wants}".lower()
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _tool_signature(plan: ExecutionPlan) -> str:
    return "|".join(s.tool for s in plan.steps)


def lookup_cached_plan(text: str, intent_raw: dict[str, Any] | None) -> ExecutionPlan | None:
    fp = _intent_fingerprint(text, intent_raw)
    row = tpl_repo.get_by_fingerprint(fp)
    if row:
        tpl_repo.touch(row["template_id"], success=True)
        steps = [PlanStep(**s) for s in json.loads(row["plan_json"] or "[]")]
        if not steps:
            return None
        return ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            steps=_hydrate_params(steps, text, intent_raw),
            summary=row.get("summary") or text[:80],
        )

    sig = None
    if intent_raw:
        tools = intent_raw.get("suggested_tools")
        if isinstance(tools, list) and tools:
            sig = "|".join(str(t) for t in tools)
    if not sig:
        return None
    row = tpl_repo.get_by_tool_signature(sig)
    if not row:
        return None
    tpl_repo.touch(row["template_id"], success=True)
    steps = [PlanStep(**s) for s in json.loads(row["plan_json"] or "[]")]
    if not steps:
        return None
    return ExecutionPlan(
        plan_id=str(uuid.uuid4()),
        steps=_hydrate_params(steps, text, intent_raw),
        summary=row.get("summary") or text[:80],
    )


def _hydrate_params(steps: list[PlanStep], text: str, intent_raw: dict[str, Any] | None) -> list[PlanStep]:
    """缓存步骤保留工具链；敏感正文仍从当次 intent 注入."""
    if not intent_raw:
        return steps
    params_map = intent_raw.get("tool_params")
    if not isinstance(params_map, dict):
        return steps
    out: list[PlanStep] = []
    for step in steps:
        override = params_map.get(step.tool)
        if isinstance(override, dict) and override:
            merged = {**step.params, **override}
            out.append(step.model_copy(update={"params": merged}))
        else:
            out.append(step)
    return out


def save_success_plan(text: str, plan: ExecutionPlan, intent_raw: dict[str, Any] | None = None) -> None:
    if not plan.steps:
        return
    fp = _intent_fingerprint(text, intent_raw)
    sig = _tool_signature(plan)
    tpl_repo.upsert(
        intent_fingerprint=fp,
        tool_signature=sig,
        intent_snapshot=json.dumps(
            {
                "goal": (intent_raw or {}).get("goal", ""),
                "user_wants": (intent_raw or {}).get("user_wants", ""),
            },
            ensure_ascii=False,
        ),
        plan_json=json.dumps([s.model_dump() for s in plan.steps], ensure_ascii=False),
        summary=plan.summary or text[:120],
    )
