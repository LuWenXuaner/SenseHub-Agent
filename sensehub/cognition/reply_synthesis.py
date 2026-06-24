"""执行完成后由应答脑生成用户向最终回复（通用，非场景硬编码）."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sensehub.cognition.prompts import ANSWER_SYSTEM
from sensehub.cognition.router import LLMRouter
from sensehub.cognition.session_context import fallback_reply_from_steps, format_history_for_brain
from sensehub.models.schemas import PlanStep, StepResult, TaskResponse


def _sanitize_output(output: Any) -> Any:
    if not isinstance(output, dict):
        return output
    out = dict(output)
    for key in ("text", "content", "html", "body", "reply", "answer"):
        val = out.get(key)
        if isinstance(val, str) and len(val) > 400:
            out[key] = val[:400] + "…"
    for key in ("saved_path", "path", "dst", "src", "screenshot_path"):
        val = out.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = Path(val).name
    title = out.get("window_title")
    if isinstance(title, str) and len(title) > 80:
        out["window_title"] = title[:80] + "…"
    return out


def build_step_payload(
    steps: list[PlanStep],
    step_results: list[StepResult],
) -> list[dict[str, Any]]:
    by_id = {r.step_id: r for r in step_results}
    payload: list[dict[str, Any]] = []
    for step in steps:
        result = by_id.get(step.step_id)
        payload.append(
            {
                "tool": step.tool,
                "description": step.description,
                "success": result.success if result else False,
                "output": _sanitize_output(result.output) if result and result.output else {},
                "error": result.error if result else None,
            }
        )
    return payload


def _execution_user_prompt(
    user_text: str,
    *,
    step_payload: list[dict[str, Any]],
    plan_summary: str = "",
    draft_answer: str = "",
    history: list[dict[str, Any]] | None = None,
) -> str:
    hist_block = format_history_for_brain(history)
    parts: list[str] = []
    if hist_block:
        parts.append(hist_block)
    parts.append(f"用户原话：{user_text}")
    if plan_summary.strip():
        parts.append(f"计划摘要：{plan_summary.strip()}")
    if draft_answer.strip():
        parts.append(f"执行脑草稿答复（可改写，勿照抄技术细节）：{draft_answer.strip()}")
    parts.append(f"各步执行结果（JSON）：{json.dumps(step_payload, ensure_ascii=False)}")
    parts.append(
        "请写面向用户的最终答复。用户已在界面看到逐步执行过程；"
        "你只需用自然中文说明任务是否完成、达成了什么，通常 1～3 句。"
        "不要罗列工具名、逐步流水账、完整磁盘路径、窗口标题或粘贴内容片段。"
        "若用户要的是写入文件/记事本等交付物，确认已交付即可，正文不必重复。"
        "若用户要的是查询/问答类结果，则根据 output 写出完整可读答案。"
        "若有步骤失败，简要说明问题并提示查看执行过程或如何改指令。"
    )
    return "\n\n".join(parts)


async def synthesize_execution_reply(
    user_text: str,
    steps: list[PlanStep],
    step_results: list[StepResult],
    *,
    plan_summary: str = "",
    draft_answer: str = "",
    agents: list[dict[str, Any]] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> str:
    """工具链执行结束后，由应答脑汇总为得体、通用的用户回复."""
    if not step_results:
        return (draft_answer or "未能完成操作，请换种说法或补充细节。").strip()

    step_payload = build_step_payload(steps, step_results)
    router = LLMRouter()
    try:
        reply = await router.chat(
            "intent",
            [
                {"role": "system", "content": ANSWER_SYSTEM},
                {
                    "role": "user",
                    "content": _execution_user_prompt(
                        user_text,
                        step_payload=step_payload,
                        plan_summary=plan_summary,
                        draft_answer=draft_answer,
                        history=history,
                    ),
                },
            ],
            temperature=0.35,
            max_tokens=1024,
        )
    except Exception:
        reply = fallback_reply_from_steps(steps, step_results, plan_summary=plan_summary)

    reply = (reply or "").strip()
    if not reply:
        reply = fallback_reply_from_steps(steps, step_results, plan_summary=plan_summary)
    if agents is not None:
        agents.append({"role": "answer", "model_role": "intent", "preview": reply[:80]})
    return reply


async def synthesize_task_reply_from_models(
    user_text: str,
    plan: Any,
    task: TaskResponse,
    *,
    agents: list[dict[str, Any]] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> str:
    if task.status == "failed":
        return task.error or "任务执行失败，请稍后重试"
    steps = list(plan.steps) if hasattr(plan, "steps") else []
    return await synthesize_execution_reply(
        user_text,
        steps,
        list(task.step_results),
        plan_summary=str(getattr(plan, "summary", "") or ""),
        agents=agents,
        history=history,
    )
