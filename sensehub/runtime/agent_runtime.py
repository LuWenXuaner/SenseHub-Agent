"""Agent 逐步执行循环（Gateway 唯一 Runtime）."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sensehub.cognition.router import LLMRouter
from sensehub.cognition.session_context import format_history_for_brain
from sensehub.cognition.tool_call_repair import extract_json_tool_call, parse_fc_arguments, promote_to_tool_calls
from sensehub.execution.tools.catalog import format_tools_for_planner
from sensehub.execution.tools.registry import REGISTRY, execute_step
from sensehub.execution.tools.schema import build_openai_tools
from sensehub.gateway import events as agent_events
from sensehub.models.schemas import ExecutionPlan, PlanStep, StepResult
from sensehub.runtime.harness_runtime import apply_sandbox_confirm_gates, gate_ui_action, review_plan_safety
from sensehub.runtime.verifier import build_factual_desktop_answer, is_desktop_run
from sensehub.security.sandbox import describe_for_planner as sandbox_rules
from sensehub.skills.loader import format_skills_prompt, match_skills
from sensehub.runtime.harness_multimodal import multimodal_prompt_addon

_MAX_ITERATIONS = 15


def _load_enabled_skill_ids() -> set[str] | None:
    from pathlib import Path

    import yaml

    path = Path(__file__).resolve().parents[2] / "config" / "skills.yaml"
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    enabled = data.get("enabled")
    if isinstance(enabled, list):
        return {str(x) for x in enabled}
    return None


def _build_system_prompt(user_text: str, intent_raw: dict | None) -> str:
    skills = match_skills(user_text, intent_raw, enabled=_load_enabled_skill_ids())
    skills_block = format_skills_prompt(skills)
    mm_block = multimodal_prompt_addon()
    mode = str((intent_raw or {}).get("action_mode", "")).lower()
    mode_hint = ""
    if mode == "answer":
        mode_hint = """
【问答模式】用户要文字结果，不要操作桌面：
- 用 returns_data=true 的工具（如 get_weather、fetch_url）按需取证，参数从用户原话提取
- 拿到工具 output 后 agent_finish，在 answer 里写出完整可读答复
- 不要要求用户点击确认（本模式无 L2 待确认任务）
"""
    elif mode == "status":
        mode_hint = "\n【状态查询】调用 get_task_status 后 agent_finish 汇总。\n"
    elif mode == "cancel":
        mode_hint = "\n【取消任务】调用 cancel_tasks 后 agent_finish 说明结果。\n"
    base = f"""你是灵枢 Agent「执行脑」。逐步使用工具完成目标，根据每步工具返回决定下一步。

可用两种方式：
1. 原生工具调用（优先）
2. 若不支持，输出 JSON：{{"thought":"","action":"tool|finish","tool":"...","params":{{}},"answer":"..."}}

原则：
- observe → verify → act；对话历史不代表当前桌面状态
- IM 内找人须先搜索再输入；finish 只陈述已验证结果
- 文件写入默认工作区相对路径；工作区外须 L2 确认
{mode_hint}
{skills_block}

{mm_block}

{format_tools_for_planner()}
{sandbox_rules()}
"""
    return base


def _risk_for_tool(tool: str) -> str:
    entry = REGISTRY.get(tool)
    return entry[1] if entry else "L1"


def _build_initial_user(
    user_text: str,
    *,
    history: list[dict[str, Any]] | None,
    intent_raw: dict[str, Any] | None,
) -> str:
    parts: list[str] = []
    hist = format_history_for_brain(history)
    if hist:
        parts.append(hist)
    parts.append(f"用户目标：{user_text}")
    if intent_raw:
        parts.append(f"意图脑：{json.dumps(intent_raw, ensure_ascii=False)}")
    parts.append("请开始第一步。")
    return "\n\n".join(parts)


def _append_tool_feedback(messages: list[dict[str, Any]], step: PlanStep, result: StepResult) -> None:
    payload = {
        "step_id": step.step_id,
        "tool": step.tool,
        "success": result.success,
        "output": result.output,
        "error": result.error,
    }
    messages.append(
        {
            "role": "tool",
            "tool_call_id": f"step_{step.step_id}",
            "content": json.dumps(payload, ensure_ascii=False),
        }
    )


class AgentRuntime:
    @staticmethod
    async def run(
        user_text: str,
        *,
        history: list[dict[str, Any]] | None = None,
        intent_raw: dict[str, Any] | None = None,
        session_id: str = "",
        max_iterations: int = _MAX_ITERATIONS,
    ) -> dict[str, Any]:
        router = LLMRouter()
        agents: list[dict[str, Any]] = [{"role": "agent_loop", "model_role": "planner", "status": "running"}]
        matched = match_skills(user_text, intent_raw, enabled=_load_enabled_skill_ids())
        for sk in matched:
            agents.append({"role": "skill", "id": sk.id, "name": sk.name})

        system = _build_system_prompt(user_text, intent_raw)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": _build_initial_user(user_text, history=history, intent_raw=intent_raw)},
        ]

        steps: list[PlanStep] = []
        step_results: list[StepResult] = []
        answer = ""
        tools = build_openai_tools()
        use_fc = True

        agent_events.emit({"type": "agent_start", "session_id": session_id, "text": user_text[:200]})

        for iteration in range(1, max_iterations + 1):
            raw: dict[str, Any] = {}
            tool_calls: list[dict[str, Any]] = []
            finish_answer: str | None = None

            try:
                if use_fc:
                    fc_result = await router.chat_with_tools_turn("planner", messages, tools)
                    if fc_result.get("mode") == "fc":
                        msg = fc_result.get("message") or {}
                        tool_calls = msg.get("tool_calls") or []
                        content = str(msg.get("content") or "").strip()
                        if content and not tool_calls:
                            repaired = extract_json_tool_call(content)
                            if repaired:
                                finish_answer, tool_calls = promote_to_tool_calls(repaired)
                        messages.append(msg)
                    else:
                        raw = fc_result.get("json") or {}
                else:
                    raw = await router.chat_json_turn("planner", messages)
            except Exception as exc:
                if use_fc and "tools" in str(exc).lower():
                    use_fc = False
                    continue
                agents.append({"role": "agent_loop", "error": str(exc), "iteration": iteration})
                break

            if tool_calls:
                for tc in tool_calls:
                    fn = tc.get("function") or {}
                    name = str(fn.get("name", "")).strip()
                    args = parse_fc_arguments(fn.get("arguments"))
                    if name == "agent_finish":
                        finish_answer = str(args.get("answer", "")).strip()
                        agents.append(
                            {
                                "role": "agent_loop",
                                "iteration": iteration,
                                "action": "finish",
                                "thought": args.get("thought", ""),
                            }
                        )
                        break
                    if not name or name not in REGISTRY:
                        messages.append(
                            {
                                "role": "user",
                                "content": f"未知工具「{name}」，请换有效工具或 agent_finish。",
                            }
                        )
                        continue
                    step, result, stop = await AgentRuntime._execute_tool_step(
                        name,
                        args,
                        steps,
                        step_results,
                        user_text,
                        intent_raw,
                        session_id,
                        agents,
                        iteration,
                    )
                    if step and result:
                        _append_tool_feedback(messages, step, result)
                    if stop:
                        if result and not result.success:
                            answer = str(result.error or "执行遇到问题")
                        return AgentRuntime._package(
                            steps, step_results, answer, agents, user_text, intent_raw, pending_confirm=stop == "confirm"
                        )
                if finish_answer is not None:
                    answer = finish_answer
                    break
                continue

            thought = str(raw.get("thought", "")).strip()
            action = str(raw.get("action", "")).lower().strip()
            agents.append(
                {
                    "role": "agent_loop",
                    "iteration": iteration,
                    "thought": thought,
                    "action": action,
                    "tool": raw.get("tool"),
                }
            )

            if action == "finish":
                answer = str(raw.get("answer", "")).strip() or thought or "已完成。"
                break

            tool = str(raw.get("tool", "")).strip()
            if not tool or tool not in REGISTRY:
                messages.append({"role": "assistant", "content": json.dumps(raw, ensure_ascii=False)})
                messages.append(
                    {"role": "user", "content": f"未知工具「{tool}」。请选有效工具或 finish。"}
                )
                continue

            params = raw.get("params") if isinstance(raw.get("params"), dict) else {}
            step, result, stop = await AgentRuntime._execute_tool_step(
                tool,
                params,
                steps,
                step_results,
                user_text,
                intent_raw,
                session_id,
                agents,
                iteration,
                thought=thought,
                raw=raw,
            )
            messages.append({"role": "assistant", "content": json.dumps(raw, ensure_ascii=False)})
            if step and result:
                _append_tool_feedback(messages, step, result)
            if stop:
                if result and not result.success:
                    answer = str(result.error or "执行遇到问题")
                return AgentRuntime._package(
                    steps, step_results, answer, agents, user_text, intent_raw, pending_confirm=stop == "confirm"
                )

        if answer and is_desktop_run(intent_raw, steps) and step_results:
            if not steps or steps[-1].tool != "active_window":
                verify_step = PlanStep(
                    step_id=len(steps) + 1,
                    tool="active_window",
                    params={},
                    risk_level="L0",
                    description="finish 前核对前台窗口",
                )
                steps.append(verify_step)
                step_results.append(execute_step(verify_step))
            answer = build_factual_desktop_answer(steps, step_results, answer)
        elif not answer:
            if step_results and all(r.success for r in step_results):
                answer = (
                    build_factual_desktop_answer(steps, step_results, "")
                    if is_desktop_run(intent_raw, steps)
                    else "任务已完成。"
                )
            elif not steps:
                answer = "未能选择合适的工具完成目标，请换种说法或补充细节。"
            else:
                answer = "执行未完全成功，请查看过程详情。"

        return AgentRuntime._package(steps, step_results, answer, agents, user_text, intent_raw)

    @staticmethod
    async def _execute_tool_step(
        tool: str,
        params: dict[str, Any],
        steps: list[PlanStep],
        step_results: list[StepResult],
        user_text: str,
        intent_raw: dict | None,
        session_id: str,
        agents: list[dict[str, Any]],
        iteration: int,
        *,
        thought: str = "",
        raw: dict | None = None,
    ) -> tuple[PlanStep | None, StepResult | None, str | None]:
        step = PlanStep(
            step_id=len(steps) + 1,
            tool=tool,
            params=params,
            risk_level=_risk_for_tool(tool),
            description=thought or tool,
        )
        prior = list(steps)
        steps.append(step)

        plan_so_far = ExecutionPlan(plan_id=str(uuid.uuid4()), steps=steps, summary=user_text[:120])
        gated = apply_sandbox_confirm_gates(plan_so_far)
        steps[-1] = gated.steps[-1]
        step = steps[-1]

        safe, reason = review_plan_safety(ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step], summary=""))
        if not safe:
            result = StepResult(step_id=step.step_id, success=False, error=reason)
            step_results.append(result)
            agent_events.emit({"type": "tool_end", "session_id": session_id, "tool": tool, "success": False})
            return step, result, None

        gate_err = gate_ui_action(step, prior, user_text, intent_raw)
        if gate_err:
            result = StepResult(step_id=step.step_id, success=False, error=gate_err)
            step_results.append(result)
            agent_events.emit({"type": "tool_end", "session_id": session_id, "tool": tool, "success": False})
            return step, result, None

        if step.requires_confirm:
            agents.append({"role": "agent_loop", "status": "wait_confirm", "iteration": iteration})
            return step, None, "confirm"

        agent_events.emit(
            {
                "type": "tool_start",
                "session_id": session_id,
                "tool": tool,
                "params": params,
                "step_id": step.step_id,
            }
        )

        if step.tool == "gui_agent":
            from sensehub.cognition.vision_agent import run_gui_agent

            out = await run_gui_agent(
                str(params.get("intent", user_text)),
                max_steps=int(params.get("max_steps", 10)),
            )
            result = StepResult(
                step_id=step.step_id,
                success=bool(out.get("success")),
                output=out if isinstance(out, dict) else {},
                error=None if out.get("success") else str(out.get("error") or "gui_agent 失败"),
            )
        else:
            result = execute_step(step)

        step_results.append(result)
        agents.append(
            {
                "role": "executor",
                "tool": tool,
                "params": params,
                "success": result.success,
                "output": result.output,
                "error": result.error,
            }
        )
        agent_events.emit(
            {
                "type": "tool_end",
                "session_id": session_id,
                "tool": tool,
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "step_id": step.step_id,
            }
        )
        if not result.success:
            return step, result, "fail"
        return step, result, None

    @staticmethod
    def _package(
        steps: list[PlanStep],
        step_results: list[StepResult],
        answer: str,
        agents: list[dict[str, Any]],
        user_text: str,
        intent_raw: dict | None,
        *,
        pending_confirm: bool = False,
    ) -> dict[str, Any]:
        plan = ExecutionPlan(plan_id=str(uuid.uuid4()), steps=steps, summary=user_text[:120])
        agents.append({"role": "agent_loop", "status": "done", "steps": len(steps)})
        agents.append({"role": "answer", "model_role": "planner", "preview": answer[:80]})
        agent_events.emit({"type": "agent_done", "answer": answer[:500]})
        if pending_confirm:
            confirm_msg = answer or "该操作涉及敏感路径或高风险步骤，请确认后才会继续执行。"
            return {
                "needs_confirm": True,
                "plan": plan,
                "steps": steps,
                "step_results": step_results,
                "answer": confirm_msg,
                "agents": agents,
            }
        return {
            "needs_confirm": False,
            "executed": True,
            "plan": plan,
            "steps": steps,
            "step_results": step_results,
            "answer": answer,
            "agents": agents,
        }
