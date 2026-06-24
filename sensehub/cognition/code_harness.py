"""灵枢 Code Harness（与 Chat、Console 完全分离）.

职责：项目上下文理解 → 变更分析 → 代码生成（coder 角色）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sensehub.cognition.prompts import CODE_ASSIST_SYSTEM
from sensehub.cognition.router import LLMRouter
from sensehub.cognition.session_context import format_history_for_brain

CODE_ANALYZER_SYSTEM = """你是灵枢 Code Harness 的「分析脑」。理解用户编程指令，输出 JSON（不要 markdown）：

{
  "goal": "用户想完成什么",
  "target_files": ["预计需要修改的相对路径"],
  "change_type": "fix|feature|refactor|explain|other",
  "risks": ["潜在风险或需用户确认的点"],
  "notes": "给代码生成脑的简短提示"
}

只分析，不写代码。"""


@dataclass
class CodeHarnessResult:
    reply: str
    edits: list[dict[str, str]]
    passes: list[dict[str, Any]] = field(default_factory=list)

    def trace_dict(self) -> dict[str, Any]:
        return {"passes": self.passes}


async def run_code_harness(
    user_text: str,
    *,
    project_root: str = "",
    project_files: list[str] | None = None,
    file_path: str = "",
    file_content: str = "",
    context_files: list[dict[str, str]] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> CodeHarnessResult:
    router = LLMRouter()
    passes: list[dict[str, Any]] = []
    hist = history or []
    hist_block = format_history_for_brain(hist)

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

    base_context = "\n\n".join(blocks) if blocks else ""
    analyze_input = user_text
    if base_context:
        analyze_input = f"{base_context}\n\n用户指令：{user_text}"
    if hist_block:
        analyze_input = f"{hist_block}\n\n{analyze_input}"

    analysis: dict[str, Any] = {}
    try:
        analysis = await router.chat_json("intent", CODE_ANALYZER_SYSTEM, analyze_input)
        passes.append({"role": "analyzer", "model": "role/intent", "summary": str(analysis.get("goal", ""))[:80]})
    except Exception as exc:
        passes.append({"role": "analyzer", "model": "role/intent", "summary": f"分析跳过: {exc}"})

    gen_input = analyze_input
    if analysis:
        gen_input += f"\n\n【Code Harness 分析】\n{json.dumps(analysis, ensure_ascii=False)}"

    result = await router.chat_json("coder", CODE_ASSIST_SYSTEM, gen_input)
    passes.append({"role": "coder", "model": "role/coder", "summary": "生成修改"})

    reply = str(result.get("reply") or "").strip()
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

    if not reply:
        reply = "已完成分析。" if edits else "未生成文件修改。"

    return CodeHarnessResult(reply=reply, edits=edits, passes=passes)
