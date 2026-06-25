"""灵枢 Code Harness（与 Chat、Console 完全分离）.

职责：项目上下文理解 → 变更分析 → 代码生成（coder 角色）。
支持 mode：agent（直接改码）、plan（先规划再改码）。model_id 为空或 auto 时使用后端 coder 角色。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from sensehub.cognition.prompts import CODE_ASSIST_SYSTEM
from sensehub.cognition.router import LLMRouter
from sensehub.cognition.session_context import format_history_for_brain
from sensehub.cognition.studio_models import StudioModelRoute, resolve_studio_model

CodeHarnessMode = Literal["agent", "plan"]

CODE_ANALYZER_SYSTEM = """你是灵枢 Code Harness 的「分析脑」。理解用户编程指令，输出 JSON（不要 markdown）：

{
  "goal": "用户想完成什么",
  "target_files": ["预计需要修改的相对路径"],
  "change_type": "fix|feature|refactor|explain|other",
  "risks": ["潜在风险或需用户确认的点"],
  "notes": "给代码生成脑的简短提示"
}

只分析，不写代码。"""

CODE_PLANNER_SYSTEM = """你是灵枢 Code Harness 的「规划脑」。根据用户指令与项目上下文，输出 JSON（不要 markdown）：

{
  "summary": "一句话概括改动方案",
  "steps": [
    {"id": 1, "action": "要做什么", "files": ["相对路径"], "detail": "具体说明"}
  ],
  "assumptions": ["假设或需用户确认的点"]
}

只规划，不写完整代码。"""


@dataclass
class CodeHarnessResult:
    reply: str
    edits: list[dict[str, str]]
    passes: list[dict[str, Any]] = field(default_factory=list)

    def trace_dict(self) -> dict[str, Any]:
        return {"passes": self.passes}


def _build_context_blocks(
    *,
    project_root: str,
    project_files: list[str] | None,
    file_path: str,
    file_content: str,
    context_files: list[dict[str, str]] | None,
) -> str:
    blocks: list[str] = []
    if project_root:
        blocks.append(f"项目根目录：{project_root}")
    files = project_files or []
    if files:
        listing = "\n".join(f"- {p}" for p in files[:120])
        blocks.append(f"项目文件列表（共 {len(files)} 个）：\n{listing}")
    if file_path and file_content is not None:
        blocks.append(f"当前聚焦文件：{file_path}\n```\n{file_content}\n```")
    for item in context_files or []:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        content = str(item.get("content") or "")
        if path and path != file_path:
            blocks.append(f"附加上下文文件：{path}\n```\n{content[:12000]}\n```")
    return "\n\n".join(blocks) if blocks else ""


async def _chat_json_with_route(
    router: LLMRouter,
    route: StudioModelRoute | None,
    role: str,
    system: str,
    user: str,
) -> dict[str, Any]:
    if route and route.available:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        text = await router.chat_provider(
            route.provider,
            route.model,
            messages,
            temperature=0.2,
            max_tokens=8192,
        )
        return router._parse_json_text(text)
    return await router.chat_json(role, system, user)


def _parse_edits(result: dict[str, Any]) -> list[dict[str, str]]:
    edits_raw = result.get("edits")
    edits: list[dict[str, str]] = []
    if isinstance(edits_raw, list):
        for item in edits_raw:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip()
            content = str(item.get("content") or "")
            if path:
                edits.append({"path": path, "content": content})
    return edits


def _format_plan_reply(plan: dict[str, Any], analysis: dict[str, Any]) -> str:
    lines: list[str] = []
    if analysis.get("goal"):
        lines.append(f"**目标**：{analysis.get('goal')}")
    summary = str(plan.get("summary") or "").strip()
    if summary:
        lines.append(f"\n**方案**：{summary}")
    steps = plan.get("steps")
    if isinstance(steps, list) and steps:
        lines.append("\n**步骤**：")
        for step in steps:
            if not isinstance(step, dict):
                continue
            sid = step.get("id", "?")
            action = step.get("action", "")
            files = step.get("files") or []
            detail = str(step.get("detail") or "").strip()
            file_hint = f" (`{', '.join(files)}`)" if files else ""
            lines.append(f"{sid}. {action}{file_hint}")
            if detail:
                lines.append(f"   {detail}")
    assumptions = plan.get("assumptions")
    if isinstance(assumptions, list) and assumptions:
        lines.append("\n**假设**：")
        for a in assumptions:
            lines.append(f"- {a}")
    return "\n".join(lines).strip()


async def run_code_harness(
    user_text: str,
    *,
    project_root: str = "",
    project_files: list[str] | None = None,
    file_path: str = "",
    file_content: str = "",
    context_files: list[dict[str, str]] | None = None,
    history: list[dict[str, Any]] | None = None,
    model_id: str = "",
    mode: CodeHarnessMode = "agent",
) -> CodeHarnessResult:
    router = LLMRouter()
    passes: list[dict[str, Any]] = []
    hist = history or []
    hist_block = format_history_for_brain(hist)

    route: StudioModelRoute | None = None
    mid = (model_id or "").strip()
    if mid and mid != "auto":
        route = resolve_studio_model(mid)

    base_context = _build_context_blocks(
        project_root=project_root,
        project_files=project_files,
        file_path=file_path,
        file_content=file_content,
        context_files=context_files,
    )
    analyze_input = user_text
    if base_context:
        analyze_input = f"{base_context}\n\n用户指令：{user_text}"
    if hist_block:
        analyze_input = f"{hist_block}\n\n{analyze_input}"

    model_label = route.label if route and route.available else "role/coder"
    effective_mode = mode if mode in ("agent", "plan") else "agent"

    analysis: dict[str, Any] = {}
    plan: dict[str, Any] = {}

    if effective_mode == "plan":
        try:
            analysis = await _chat_json_with_route(
                router, None, "intent", CODE_ANALYZER_SYSTEM, analyze_input
            )
            passes.append(
                {"role": "analyzer", "model": "role/intent", "summary": str(analysis.get("goal", ""))[:80]}
            )
        except Exception as exc:
            passes.append({"role": "analyzer", "model": "role/intent", "summary": f"分析跳过: {exc}"})

        plan_input = analyze_input
        if analysis:
            plan_input += f"\n\n【Code Harness 分析】\n{json.dumps(analysis, ensure_ascii=False)}"
        try:
            plan = await _chat_json_with_route(
                router, None, "planner", CODE_PLANNER_SYSTEM, plan_input
            )
            passes.append(
                {"role": "planner", "model": "role/planner", "summary": str(plan.get("summary", ""))[:80]}
            )
        except Exception as exc:
            passes.append({"role": "planner", "model": "role/planner", "summary": f"规划跳过: {exc}"})

    gen_input = analyze_input
    if analysis:
        gen_input += f"\n\n【Code Harness 分析】\n{json.dumps(analysis, ensure_ascii=False)}"
    if plan:
        gen_input += f"\n\n【Code Harness 计划】\n{json.dumps(plan, ensure_ascii=False)}"

    passes.append(
        {
            "role": "mode",
            "model": model_label,
            "summary": "Plan 先规划后改码" if effective_mode == "plan" else "Agent 直接改码",
        }
    )

    coder_role = "coder"
    result = await _chat_json_with_route(router, route, coder_role, CODE_ASSIST_SYSTEM, gen_input)
    passes.append({"role": "coder", "model": model_label, "summary": "生成修改"})

    reply = str(result.get("reply") or "").strip()
    edits = _parse_edits(result)

    if effective_mode == "plan" and plan:
        plan_block = _format_plan_reply(plan, analysis)
        if reply:
            reply = f"{plan_block}\n\n---\n\n{reply}"
        else:
            reply = plan_block

    if not reply:
        reply = "已完成分析。" if edits else "未生成文件修改。"

    return CodeHarnessResult(reply=reply, edits=edits, passes=passes)
