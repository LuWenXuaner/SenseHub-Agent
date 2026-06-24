"""Agent 逐步执行循环（Gateway 唯一 Runtime）."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sensehub.cognition.router import LLMRouter
from sensehub.cognition.session_context import format_history_for_brain
from sensehub.cognition.tool_call_repair import extract_json_tool_call, parse_fc_arguments, promote_to_tool_calls
from sensehub.cognition.console_harness_policy import harness_policy_block
from sensehub.execution.kill_switch import is_killed
from sensehub.cognition.action_synthesis import (
    CONTENT_FIELD_BY_TOOL,
    gather_evidence,
    needs_content_synthesis,
    post_gather_hint,
    synthesize_tool_params,
)
from sensehub.execution.tools.catalog import format_tools_for_planner, tool_returns_data
from sensehub.execution.tools.registry import REGISTRY, execute_step
from sensehub.execution.tools.schema import build_openai_tools, validate_tool_params
from sensehub.gateway import events as agent_events
from sensehub.models.schemas import ExecutionPlan, PlanStep, StepResult
from sensehub.runtime.harness_runtime import (
    apply_sandbox_confirm_gates,
    gate_login_screen,
    gate_ui_action,
    needs_im_search_flow,
    review_plan_safety,
    targets_im_app,
)
from sensehub.runtime.verifier import is_desktop_run
from sensehub.cognition.atomic_reply import fast_atomic_reply, should_fast_atomic_reply
from sensehub.cognition.reply_synthesis import synthesize_execution_reply
from sensehub.execution.tools.desktop import schedule_refocus_from_steps
from sensehub.security.sandbox import describe_for_planner as sandbox_rules
from sensehub.skills.loader import format_skills_prompt, match_skills
from sensehub.runtime.harness_multimodal import multimodal_prompt_addon

_MAX_ITERATIONS = 15
_MAX_RECOVERY_FAILURES = 3
_OBSERVE_ONLY_TOOLS = frozenset({"list_windows", "active_window", "screenshot", "browser_status", "browser_tabs"})
_SEARCH_HINTS = ("搜索", "查", "资料", "网页", "新闻", "全网", "wiki", "官网", "文档")
_BROWSER_HINTS = ("网站", "网页", "浏览器", "打开网址", "open url")
_FILE_HINTS = ("保存", "写入", "文件", "文档", "导出", "txt", "docx", "xlsx", "ppt")
_DESKTOP_HINTS = ("打开", "点击", "输入", "窗口", "桌面", "记事本", "微信", "qq", "钉钉")
_NOTEPAD_HINTS = ("记事本", "notepad")
_INPUT_HINTS = ("输入", "写入", "打字", "键入", "粘贴")


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
    wants = str((intent_raw or {}).get("user_wants", "")).lower()
    if wants in {"both", "desktop_action"} and mode == "execute":
        mode_hint += """
【通用执行链】returns_data 取证 → 根据 output 撰写完整正文 → action 工具（notepad_type_save/write_file 等）
- 正文参数须由你根据取证结果填写，禁止占位语；系统必要时会调用「内容合成脑」辅助
- 可 finish 向用户说明结果，但用户明确要求写入文件/记事本的须先完成写入工具"""
    base = f"""你是灵枢 Agent「执行脑」。逐步使用工具完成目标，根据每步工具返回决定下一步。

可用两种方式：
1. 原生工具调用（优先）
2. 若不支持，输出 JSON：{{"thought":"","action":"tool|finish","tool":"...","params":{{}},"answer":"..."}}

原则：
- observe → gather(returns_data) → compose → act；对话历史不代表当前桌面状态
- 意图脑 suggested_tools / tool_params 为参考；正文类参数（text/content）须据取证 output 完整撰写
- 记事本「打开+输入+保存」：notepad_type_save(text=正文, filename=…)；完成后按需 close_app(name=应用名)
- 微信找人发消息：从用户原话理解完整 contact 与 message，调用 wechat_send_message(contact=, message=)；勿截断联系人名；工具内首步置前一次，之后默认焦点正确；不发送则 send=false
- finish 只陈述已验证结果；用户要「写入/保存」时不得在未执行写入工具前 finish
- 禁止陷入“只观察不行动”：连续观察后必须转入 open_app/type_text/write_file 等执行动作
- 需账号/扫码登录的应用（微信/QQ/钉钉等）：不代替用户登录；见登录界面则 agent_finish 提示用户先自行登录
- 相对路径文件默认保存到用户配置的默认保存路径；用户指定了其他路径则从其指定
- Word/Excel/PPT：优先 generate_document；记事本纯文本可用 write_file
{mode_hint}
{skills_block}
{harness_policy_block()}

{mm_block}

{format_tools_for_planner()}
{sandbox_rules()}
"""
    return base


def _risk_for_tool(tool: str) -> str:
    entry = REGISTRY.get(tool)
    return entry[1] if entry else "L1"


def _intent_brief(intent_raw: dict[str, Any] | None) -> str:
    if not intent_raw:
        return ""
    lines = [
        "【意图脑解析 — 执行时请优先采用】",
        f"- goal: {intent_raw.get('goal', '')}",
    ]
    tools = intent_raw.get("suggested_tools")
    if tools:
        lines.append(f"- suggested_tools（按序）: {', '.join(str(t) for t in tools)}")
    params = intent_raw.get("tool_params")
    if isinstance(params, dict) and params:
        lines.append("- tool_params（参数须原样传给对应工具，勿臆造）：")
        for name, p in params.items():
            lines.append(f"  - {name}: {json.dumps(p, ensure_ascii=False)}")
    notes = str(intent_raw.get("notes") or "").strip()
    if notes:
        lines.append(f"- notes: {notes}")
    lines.append(
        "- 参数纪律：正文类字段由执行脑根据取证 output 撰写；"
        "suggested_tools 按序执行完毕后再 agent_finish"
    )
    return "\n".join(lines)


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
    brief = _intent_brief(intent_raw)
    if brief:
        parts.append(brief)
    elif intent_raw:
        parts.append(f"意图脑：{json.dumps(intent_raw, ensure_ascii=False)}")
    parts.append("请根据意图脑建议的工具与参数开始执行；若无建议则自行选工具。")
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


def _append_post_tool_hints(
    messages: list[dict[str, Any]],
    step: PlanStep,
    result: StepResult,
    user_text: str,
    intent_raw: dict[str, Any] | None,
) -> None:
    if not result.success:
        return
    if tool_returns_data(step.tool):
        hint = post_gather_hint(user_text, step.tool, intent_raw)
        if hint:
            messages.append({"role": "user", "content": hint})


def _desktop_goal_incomplete(user_text: str, steps: list[PlanStep]) -> str | None:
    """用户目标含输入/保存时，仅 open_app 不算完成."""
    tools = {s.tool for s in steps}
    low = user_text.lower()
    notepad_task = any(h in user_text for h in _NOTEPAD_HINTS) or "notepad" in low
    wants_input = any(h in user_text for h in _INPUT_HINTS)
    wants_save = "保存" in user_text

    if notepad_task and wants_input and wants_save and "notepad_type_save" not in tools:
        if not all(t in tools for t in ("type_text", "save_notepad")) and "notepad_type_save" not in tools:
            return "用户要求记事本输入并保存：请用 notepad_type_save 或 open_app→type_text→save_notepad。"
    if notepad_task and wants_input and "type_text" not in tools and "notepad_type_save" not in tools:
        return (
            "用户要求向记事本输入内容：请继续 type_text(app=记事本/notepad) 粘贴，"
            "不要仅 open_app 就结束。"
        )
    if notepad_task and wants_save and "save_notepad" not in tools and "notepad_type_save" not in tools:
        return "用户要求保存记事本：请在 type_text 之后调用 save_notepad 或 notepad_type_save，再 finish。"
    wants_close = any(k in user_text for k in ("关闭", "关掉", "退出"))
    if wants_close and "close_app" not in tools:
        return "用户要求关闭应用：请完成输入/保存后调用 close_app，再 finish。"
    return None


def _premature_finish(
    steps: list[PlanStep],
    intent_raw: dict | None,
    user_text: str = "",
) -> bool:
    """仅观察、未实际操作桌面时禁止 agent_finish."""
    if not steps:
        return True
    if _desktop_goal_incomplete(user_text, steps):
        return True
    if any(s.tool not in _OBSERVE_ONLY_TOOLS for s in steps):
        return False
    wants = str((intent_raw or {}).get("user_wants", "")).lower()
    mode = str((intent_raw or {}).get("action_mode", "")).lower()
    return wants in {"desktop_action", "both"} or mode == "execute"


def _pending_suggested_tools(
    intent_raw: dict[str, Any] | None,
    steps: list[PlanStep],
) -> list[tuple[str, dict[str, Any]]]:
    """意图脑 suggested_tools 中尚未执行的步骤（按顺序）."""
    if not intent_raw:
        return []
    suggested = intent_raw.get("suggested_tools")
    params_map = intent_raw.get("tool_params")
    if not isinstance(suggested, list) or not isinstance(params_map, dict):
        return []
    done = {s.tool for s in steps}
    pending: list[tuple[str, dict[str, Any]]] = []
    for name in suggested:
        tool = str(name).strip()
        if not tool or tool not in REGISTRY or tool in done:
            continue
        raw = params_map.get(tool)
        params = dict(raw) if isinstance(raw, dict) else {}
        pending.append((tool, params))
    return pending


def _normalize_intent_tool_params(tool: str, params: dict[str, Any], user_text: str) -> dict[str, Any]:
    """修正意图脑偶发的窗口标题偏差（Win11 记事本标题为英文 Notepad）."""
    if tool != "close_app":
        return params
    low = user_text.lower()
    if "记事本" in user_text or "notepad" in low:
        return {"name": "notepad"}
    out = {k: v for k, v in params.items() if k in ("name", "title", "timeout") and v not in (None, "")}
    if out.get("name") or out.get("title"):
        return out
    return params


def _fallback_close_tools(user_text: str, steps: list[PlanStep]) -> list[tuple[str, dict[str, Any]]]:
    """用户要求关闭但意图脑未列出时，补一条 close_app."""
    tools = {s.tool for s in steps}
    if "close_app" in tools:
        return []
    if not any(k in user_text for k in ("关闭", "关掉", "退出")):
        return []
    low = user_text.lower()
    if "记事本" in user_text or "notepad" in low:
        return [("close_app", {"name": "notepad"})]
    return []


def _finish_block_message(steps: list[PlanStep], intent_raw: dict | None, user_text: str) -> str:
    incomplete = _desktop_goal_incomplete(user_text, steps)
    if incomplete:
        return incomplete
    return (
        "尚未执行 open_app / type_text / hotkey 等实际操作，"
        "请勿仅 list_windows 就结束。请继续完成用户目标。"
    )


def _observe_stall_warning(
    steps: list[PlanStep], intent_raw: dict | None, user_text: str = ""
) -> str | None:
    """连续观察无动作时，给执行脑纠偏提示。"""
    if not _premature_finish(steps, intent_raw, user_text):
        return None
    if len(steps) < 3:
        return None
    recent = steps[-3:]
    if not all(s.tool in _OBSERVE_ONLY_TOOLS for s in recent):
        return None
    if len({s.tool for s in recent}) == 1:
        same = recent[0].tool
        return f"你已连续 3 次仅调用 {same}。请改为实际执行工具（如 open_app/type_text/write_file 等）。"
    return "你已连续 3 步仅观察。请改为实际执行工具（如 open_app/type_text/write_file 等）。"


def _recommended_tool_order(
    user_text: str,
    intent_raw: dict[str, Any] | None,
    step_results: list[StepResult],
) -> list[str]:
    """基于目标与最近失败，给工具调用做轻量排序提示。"""
    tools = list(REGISTRY.keys())
    scores = {name: 0 for name in tools}
    mode = str((intent_raw or {}).get("action_mode", "")).lower()
    wants = str((intent_raw or {}).get("user_wants", "")).lower()

    if mode in {"answer", "status", "cancel"}:
        for name in ("web_search_results", "fetch_url", "get_weather", "get_task_status", "cancel_tasks"):
            if name in scores:
                scores[name] += 8

    if any(k in user_text for k in _SEARCH_HINTS):
        for name in ("web_search_results", "fetch_url", "browser_navigate", "browser_snapshot", "browser_act"):
            if name in scores:
                scores[name] += 6

    if any(k in user_text for k in _BROWSER_HINTS):
        for name in ("open_url", "web_search", "browser_navigate", "browser_snapshot", "browser_act"):
            if name in scores:
                scores[name] += 4

    if any(k in user_text for k in _FILE_HINTS):
        for name in ("write_file", "generate_document", "read_file", "list_dir", "file_exists", "save_notepad"):
            if name in scores:
                scores[name] += 5

    if wants in {"desktop_action", "both"} or any(k in user_text for k in _DESKTOP_HINTS):
        for name in ("open_app", "focus_window", "active_window", "type_text", "press_key", "hotkey"):
            if name in scores:
                scores[name] += 5

    if needs_im_search_flow(user_text, intent_raw):
        if "wechat_send_message" in scores:
            scores["wechat_send_message"] += 14
        for name in ("hotkey", "press_key", "open_app", "type_text"):
            if name in scores:
                scores[name] += 6

    if "保存" in user_text and any(h in user_text for h in _NOTEPAD_HINTS + ("notepad",)):
        for name in ("notepad_type_save", "save_notepad", "type_text"):
            if name in scores:
                scores[name] += 10
    if any(k in user_text for k in ("关闭", "关掉", "退出")):
        if "close_app" in scores:
            scores["close_app"] += 12
    if any(h in user_text for h in _INPUT_HINTS) and any(h in user_text for h in _NOTEPAD_HINTS + ("notepad",)):
        if "type_text" in scores:
            scores["type_text"] += 8

    # 失败后调高替代工具，避免重复撞同一条路径
    recent_fail = [r for r in step_results[-5:] if not r.success]
    for idx, fail in enumerate(reversed(recent_fail), start=1):
        penalty = max(1, 5 - idx)
        # StepResult 不含 tool，回退从错误信息启发替代
        err = str(fail.error or "")
        if "web_search" in err or "搜索" in err:
            for name in ("web_search_results", "fetch_url"):
                if name in scores:
                    scores[name] += 3
        if "窗口" in err or "未找到" in err:
            for name in ("open_app", "focus_window", "list_windows", "active_window"):
                if name in scores:
                    scores[name] += 2
        if "参数错误" in err:
            for name in tools:
                scores[name] += 0
        if "未知工具" in err:
            if "gui_agent" in scores:
                scores["gui_agent"] -= penalty

    # 高频兜底工具默认后置，避免过早走重型路线
    if "gui_agent" in scores:
        scores["gui_agent"] -= 3
    if "run_command" in scores:
        scores["run_command"] -= 2

    ordered = sorted(tools, key=lambda n: (scores.get(n, 0), n), reverse=True)
    return ordered


def _should_replan_after_failure(error: str, failures: int) -> bool:
    if failures >= _MAX_RECOVERY_FAILURES:
        return False
    fatal_markers = ("请先在本地手动登录", "用户已停止执行", "Kill Switch", "需你确认后")
    if any(mark in error for mark in fatal_markers):
        return False
    return True


def _replan_hint(tool: str, error: str) -> str:
    return (
        f"上一步工具 {tool} 执行失败：{error}。"
        "请调整策略：可更换工具、修正参数，或先观察再操作；不要重复相同失败调用。"
    )


class AgentRuntime:
    @staticmethod
    async def _maybe_synthesize_content(
        tool: str,
        params: dict[str, Any],
        steps: list[PlanStep],
        step_results: list[StepResult],
        user_text: str,
        intent_raw: dict | None,
        agents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """取证后正文缺失/占位时，调用内容合成脑（通用 LLM，非场景模板）."""
        evidence = gather_evidence(steps, step_results)
        if not needs_content_synthesis(tool, params, evidence):
            return params
        field = CONTENT_FIELD_BY_TOOL.get(tool, "text")
        agents.append({"role": "synthesizer", "target_tool": tool, "status": "running"})
        try:
            merged = await synthesize_tool_params(
                user_text, intent_raw, tool, params, evidence
            )
            agents.append(
                {
                    "role": "synthesizer",
                    "target_tool": tool,
                    "status": "done",
                    "content_field": field,
                    "preview": str(merged.get(field, ""))[:120],
                }
            )
            return merged
        except Exception as exc:
            agents.append(
                {
                    "role": "synthesizer",
                    "target_tool": tool,
                    "status": "error",
                    "error": str(exc),
                }
            )
            raise

    @staticmethod
    async def _flush_intent_suggested_tools(
        intent_raw: dict[str, Any] | None,
        steps: list[PlanStep],
        step_results: list[StepResult],
        user_text: str,
        session_id: str,
        agents: list[dict[str, Any]],
    ) -> None:
        """跑完意图脑规划里尚未执行的 suggested_tools（及关闭类兜底）."""
        for _ in range(8):
            pending = _pending_suggested_tools(intent_raw, steps)
            if not pending:
                pending = _fallback_close_tools(user_text, steps)
            if not pending:
                break
            tool, params = pending[0]
            params = _normalize_intent_tool_params(tool, params, user_text)
            _, result, stop = await AgentRuntime._execute_tool_step(
                tool,
                params,
                steps,
                step_results,
                user_text,
                intent_raw,
                session_id,
                agents,
                len(steps) + 1,
                thought=f"意图链：{tool}",
            )
            if stop or (result and not result.success):
                break

    @staticmethod
    async def run_plan(
        plan: ExecutionPlan,
        user_text: str,
        *,
        history: list[dict[str, Any]] | None = None,
        intent_raw: dict[str, Any] | None = None,
        session_id: str = "",
    ) -> dict[str, Any]:
        """按既定步骤顺序执行（高置信度捷径，不经过 LLM 逐步选工具）."""
        _ = history
        agents: list[dict[str, Any]] = [
            {"role": "agent_loop", "model_role": "planner", "status": "quick_plan"},
            {"role": "quick_plan", "summary": plan.summary, "step_count": len(plan.steps)},
        ]
        steps: list[PlanStep] = []
        step_results: list[StepResult] = []
        answer = ""

        agent_events.emit({"type": "agent_start", "session_id": session_id, "text": user_text[:200]})

        for planned in plan.steps:
            if is_killed():
                answer = "用户已停止执行。"
                break
            step, result, stop = await AgentRuntime._execute_tool_step(
                planned.tool,
                planned.params if isinstance(planned.params, dict) else {},
                steps,
                step_results,
                user_text,
                intent_raw,
                session_id,
                agents,
                planned.step_id,
                thought=planned.description or planned.tool,
            )
            if stop == "confirm":
                answer = "该操作需你确认后才会继续执行。"
                return AgentRuntime._package(
                    steps, step_results, answer, agents, user_text, intent_raw, pending_confirm=True
                )
            if stop == "fail" or (result and not result.success):
                answer = str(result.error if result else "执行失败")
                break

        if not answer:
            if step_results:
                if should_fast_atomic_reply(steps, step_results):
                    answer = fast_atomic_reply(steps, step_results, plan_summary=plan.summary)
                elif any(not r.success for r in step_results):
                    failed = next((r for r in reversed(step_results) if not r.success), None)
                    answer = str(failed.error if failed else "执行失败")
                else:
                    answer = await synthesize_execution_reply(
                        user_text,
                        steps,
                        step_results,
                        plan_summary=plan.summary,
                        agents=agents,
                    )
            else:
                answer = "未能执行计划步骤。"

        return AgentRuntime._package(steps, step_results, answer, agents, user_text, intent_raw)

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
        use_fc = True
        recover_failures = 0

        agent_events.emit({"type": "agent_start", "session_id": session_id, "text": user_text[:200]})

        for iteration in range(1, max_iterations + 1):
            if is_killed():
                answer = "用户已停止执行。"
                agents.append({"role": "agent_loop", "status": "cancelled", "iteration": iteration})
                break

            raw: dict[str, Any] = {}
            tool_calls: list[dict[str, Any]] = []
            finish_answer: str | None = None

            try:
                if use_fc:
                    ordered_tools = _recommended_tool_order(user_text, intent_raw, step_results)
                    tools = build_openai_tools(ordered_names=ordered_tools)
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
                pending = _pending_suggested_tools(intent_raw, steps) or _fallback_close_tools(
                    user_text, steps
                )
                if pending and step_results and any(r.success for r in step_results):
                    await AgentRuntime._flush_intent_suggested_tools(
                        intent_raw, steps, step_results, user_text, session_id, agents
                    )
                    break
                agents.append({"role": "agent_loop", "error": str(exc), "iteration": iteration})
                break

            if tool_calls:
                for tc in tool_calls:
                    fn = tc.get("function") or {}
                    name = str(fn.get("name", "")).strip()
                    args = parse_fc_arguments(fn.get("arguments"))
                    if name == "agent_finish":
                        if _premature_finish(steps, intent_raw, user_text):
                            messages.append(
                                {
                                    "role": "user",
                                    "content": _finish_block_message(steps, intent_raw, user_text),
                                }
                            )
                            continue
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
                    agents.append(
                        {
                            "role": "agent_loop",
                            "iteration": iteration,
                            "action": "tool",
                            "tool": name,
                            "status": "done",
                        }
                    )
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
                        _append_post_tool_hints(messages, step, result, user_text, intent_raw)
                        if result.success:
                            recover_failures = 0
                        warn = _observe_stall_warning(steps, intent_raw, user_text)
                        if warn:
                            messages.append({"role": "user", "content": warn})
                    if stop:
                        if stop == "fail" and result and not result.success:
                            err = str(result.error or "执行失败")
                            if _should_replan_after_failure(err, recover_failures):
                                recover_failures += 1
                                messages.append({"role": "user", "content": _replan_hint(name, err)})
                                break
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
                if _premature_finish(steps, intent_raw, user_text):
                    messages.append(
                        {
                            "role": "user",
                            "content": _finish_block_message(steps, intent_raw, user_text),
                        }
                    )
                    continue
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
                _append_post_tool_hints(messages, step, result, user_text, intent_raw)
                if result.success:
                    recover_failures = 0
                warn = _observe_stall_warning(steps, intent_raw, user_text)
                if warn:
                    messages.append({"role": "user", "content": warn})
            if stop:
                if stop == "fail" and result and not result.success:
                    err = str(result.error or "执行失败")
                    if _should_replan_after_failure(err, recover_failures):
                        recover_failures += 1
                        messages.append({"role": "user", "content": _replan_hint(tool, err)})
                        continue
                if result and not result.success:
                    answer = str(result.error or "执行遇到问题")
                if step_results and stop != "confirm":
                    if should_fast_atomic_reply(steps, step_results):
                        answer = fast_atomic_reply(steps, step_results, plan_summary=answer or "")
                    else:
                        answer = await synthesize_execution_reply(
                            user_text,
                            steps,
                            step_results,
                            draft_answer=answer,
                            agents=agents,
                            history=history,
                        )
                return AgentRuntime._package(
                    steps, step_results, answer, agents, user_text, intent_raw, pending_confirm=stop == "confirm"
                )

        await AgentRuntime._flush_intent_suggested_tools(
            intent_raw, steps, step_results, user_text, session_id, agents
        )
        if step_results:
            if should_fast_atomic_reply(steps, step_results):
                answer = fast_atomic_reply(steps, step_results, plan_summary=answer or "")
            else:
                answer = await synthesize_execution_reply(
                    user_text,
                    steps,
                    step_results,
                    draft_answer=answer,
                    agents=agents,
                    history=history,
                )
        elif not answer:
            answer = (
                "未能选择合适的工具完成目标，请换种说法或补充细节。"
                if not steps
                else "执行未完全成功，请查看过程详情。"
            )

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
        if tool in ("type_text", "save_notepad") and not params.get("app"):
            for ps in reversed(steps):
                if ps.tool == "open_app":
                    name = str(ps.params.get("name", "")).strip()
                    if name:
                        low = name.lower()
                        if low in ("notepad", "记事本") or "notepad" in low:
                            params = {**params, "app": name}
                    break

        try:
            params = await AgentRuntime._maybe_synthesize_content(
                tool, params, steps, step_results, user_text, intent_raw, agents
            )
        except Exception as exc:
            step = PlanStep(
                step_id=len(steps) + 1,
                tool=tool,
                params=params,
                risk_level=_risk_for_tool(tool),
                description=thought or tool,
            )
            steps.append(step)
            result = StepResult(step_id=step.step_id, success=False, error=str(exc))
            step_results.append(result)
            agents.append(
                {
                    "role": "executor",
                    "step_id": step.step_id,
                    "tool": tool,
                    "params": params,
                    "success": False,
                    "error": str(exc),
                }
            )
            return step, result, "fail"

        step = PlanStep(
            step_id=len(steps) + 1,
            tool=tool,
            params=params,
            risk_level=_risk_for_tool(tool),
            description=thought or tool,
        )
        prior = list(steps)
        steps.append(step)

        param_err = validate_tool_params(tool, params)
        if param_err:
            result = StepResult(step_id=step.step_id, success=False, error=f"参数错误：{param_err}")
            step_results.append(result)
            agent_events.emit(
                {
                    "type": "tool_end",
                    "session_id": session_id,
                    "tool": tool,
                    "success": False,
                    "error": result.error,
                    "step_id": step.step_id,
                }
            )
            return step, result, "fail"

        plan_so_far = ExecutionPlan(plan_id=str(uuid.uuid4()), steps=steps, summary=user_text[:120])
        gated = apply_sandbox_confirm_gates(plan_so_far)
        steps[-1] = gated.steps[-1]
        step = steps[-1]

        safe, reason = review_plan_safety(ExecutionPlan(plan_id=str(uuid.uuid4()), steps=[step], summary=""))
        if not safe:
            result = StepResult(step_id=step.step_id, success=False, error=reason)
            step_results.append(result)
            agent_events.emit({"type": "tool_end", "session_id": session_id, "tool": tool, "success": False})
            return step, result, "fail"

        gate_err = gate_ui_action(step, prior, user_text, intent_raw)
        if gate_err:
            result = StepResult(step_id=step.step_id, success=False, error=gate_err)
            step_results.append(result)
            agent_events.emit({"type": "tool_end", "session_id": session_id, "tool": tool, "success": False})
            return step, result, "fail"

        if step.tool == "wechat_send_message":
            from sensehub.cognition.wechat_params import resolve_wechat_message_params

            try:
                params = await resolve_wechat_message_params(user_text, params)
                step = PlanStep(
                    step_id=step.step_id,
                    tool=step.tool,
                    params=params,
                    risk_level=step.risk_level,
                    description=step.description,
                    requires_confirm=step.requires_confirm,
                )
                steps[-1] = step
            except Exception as exc:
                result = StepResult(step_id=step.step_id, success=False, error=str(exc))
                step_results.append(result)
                agents.append(
                    {
                        "role": "executor",
                        "step_id": step.step_id,
                        "tool": tool,
                        "params": params,
                        "success": False,
                        "error": str(exc),
                    }
                )
                return step, result, "fail"

        if step.requires_confirm:
            agents.append({"role": "agent_loop", "status": "wait_confirm", "iteration": iteration})
            return step, None, "confirm"

        if is_killed():
            result = StepResult(step_id=step.step_id, success=False, error="用户已停止执行")
            step_results.append(result)
            agent_events.emit({"type": "tool_end", "session_id": session_id, "tool": tool, "success": False})
            return step, result, "fail"

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

        if result.success:
            login_msg = gate_login_screen(tool, result.output if isinstance(result.output, dict) else {}, user_text, intent_raw)
            if not login_msg and isinstance(result.output, dict) and result.output.get("login_screen_detected"):
                if targets_im_app(user_text, intent_raw, result.output):
                    login_msg = (
                        "检测到应用处于登录/扫码界面。请先在本地手动登录后再继续。"
                    )
            if login_msg:
                result = StepResult(
                    step_id=step.step_id,
                    success=False,
                    output=result.output,
                    error=login_msg,
                )

        step_results.append(result)
        agents.append(
            {
                "role": "executor",
                "step_id": step.step_id,
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
        if is_desktop_run(intent_raw, steps) and steps and not pending_confirm:
            schedule_refocus_from_steps(steps)
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
