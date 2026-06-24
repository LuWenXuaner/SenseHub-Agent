"""灵枢 Chat Harness（与 Console、Code 完全分离）.

创新点：每轮对话前用小模型（intent / Qwen3-8B）提取历史记忆，
再与当前消息一并交给用户所选生成模型，避免追问断档。

编排链：记忆脑 → 深度路由 → 分析脑 → [规划脑] → 生成脑 → [质检脑] → [精炼脑]
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

import yaml

from sensehub.cognition.chat_memory import extract_chat_memory, format_memory_block, format_tail_turns
from sensehub.cognition.prompts import (
    STUDIO_ANALYZER_SYSTEM,
    STUDIO_CRITIC_SYSTEM,
    STUDIO_PLANNER_SYSTEM,
    STUDIO_REFINE_USER_TEMPLATE,
    build_studio_chat_system,
    studio_skill_hint,
)
from sensehub.cognition.router import LLMRouter
from sensehub.cognition.session_context import format_history_for_brain
from sensehub.cognition.studio_models import StudioModelRoute, provider_display_label
from sensehub.settings import CONFIG_DIR

CONFIG_PATH = CONFIG_DIR / "chat_harness.yaml"

Strategy = Literal["direct", "guided", "decompose"]

_COMPLEX_MARKERS = (
    "分析",
    "对比",
    "比较",
    "设计",
    "方案",
    "步骤",
    "实现",
    "优化",
    "证明",
    "为什么",
    "如何",
    "怎么",
    "刚才",
    "上面",
    "之前",
    "那个",
    "这个",
    "继续",
    "架构",
    "规划",
    "总结",
    "评估",
    "代码",
    "debug",
    "compare",
    "design",
    "implement",
    "explain",
    "write",
)


@dataclass
class MemoryConfig:
    enabled: bool = True
    extractor_role: str = "intent"
    min_history_messages: int = 1
    tail_raw_turns: int = 2


@dataclass
class ChatHarnessConfig:
    enabled: bool = True
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    complexity_threshold_guided: int = 1
    complexity_threshold_decompose: int = 3
    analyzer_role: str = "intent"
    enable_critic: bool = True
    enable_refine: bool = True
    max_refine_passes: int = 1


@dataclass
class HarnessPass:
    role: str
    model: str
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatHarnessResult:
    reply: str
    strategy: Strategy
    complexity_score: int
    model_used: str
    passes: list[HarnessPass] = field(default_factory=list)

    def trace_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "complexity_score": self.complexity_score,
            "model_used": self.model_used,
            "passes": [
                {"role": p.role, "model": p.model, "summary": p.summary, **p.detail}
                for p in self.passes
            ],
        }


_config_cache: tuple[float, ChatHarnessConfig] | None = None


def load_chat_harness_config() -> ChatHarnessConfig:
    global _config_cache
    mtime = CONFIG_PATH.stat().st_mtime if CONFIG_PATH.exists() else 0.0
    if _config_cache and _config_cache[0] == mtime:
        return _config_cache[1]

    cfg = ChatHarnessConfig()
    if CONFIG_PATH.exists():
        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        if isinstance(raw, dict):
            mem_raw = raw.get("memory") if isinstance(raw.get("memory"), dict) else {}
            memory = MemoryConfig(
                enabled=bool(mem_raw.get("enabled", True)),
                extractor_role=str(mem_raw.get("extractor_role") or "intent"),
                min_history_messages=int(mem_raw.get("min_history_messages", 1)),
                tail_raw_turns=int(mem_raw.get("tail_raw_turns", 2)),
            )
            cfg = ChatHarnessConfig(
                enabled=bool(raw.get("enabled", True)),
                memory=memory,
                complexity_threshold_guided=int(raw.get("complexity_threshold_guided", 1)),
                complexity_threshold_decompose=int(raw.get("complexity_threshold_decompose", 3)),
                analyzer_role=str(raw.get("analyzer_role") or "intent"),
                enable_critic=bool(raw.get("enable_critic", True)),
                enable_refine=bool(raw.get("enable_refine", True)),
                max_refine_passes=int(raw.get("max_refine_passes", 1)),
            )
    _config_cache = (mtime, cfg)
    return cfg


def estimate_complexity(user_text: str, history: list[dict[str, Any]], cfg: ChatHarnessConfig) -> tuple[int, Strategy]:
    score = 0
    t = user_text.strip()
    if len(t) > 100:
        score += 1
    if len(t) > 280:
        score += 1
    questions = t.count("?") + t.count("？")
    if questions >= 2:
        score += 2
    elif questions == 1 and len(t) > 60:
        score += 1
    if any(m in t for m in _COMPLEX_MARKERS):
        score += 2
    if len(history) >= 2:
        score += 1
    if "【" in t and "】" in t:
        score += 1
    if re.search(r"```", t):
        score += 1

    if score >= cfg.complexity_threshold_decompose:
        strategy: Strategy = "decompose"
    elif score >= cfg.complexity_threshold_guided:
        strategy = "guided"
    else:
        strategy = "direct"
    return score, strategy


class _ModelBridge:
    def __init__(self, router: LLMRouter, route: StudioModelRoute | None, analyzer_role: str) -> None:
        self.router = router
        self.route = route
        self.analyzer_role = analyzer_role

    @property
    def user_model_label(self) -> str:
        if self.route and self.route.available:
            return f"{self.route.provider}/{self.route.model}"
        return "intent/default"

    async def harness_json(self, system: str, user: str) -> dict[str, Any]:
        text = await self.router.chat(
            self.analyzer_role,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=768,
        )
        return _parse_json_loose(text)

    async def generate(self, system: str, user: str, *, max_tokens: int = 2048) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        if self.route and self.route.available:
            return await self.router.chat_provider(
                self.route.provider,
                self.route.model,
                messages,
                temperature=0.5,
                max_tokens=max_tokens,
            )
        return await self.router.chat("intent", messages, temperature=0.5, max_tokens=max_tokens)


def _parse_json_loose(text: str) -> dict[str, Any]:
    text = text.strip()
    text = re.sub(
        r"<\s*think\s*>.*?<\s*/\s*think\s*>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end])
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _build_system(route: StudioModelRoute | None) -> str:
    if route and route.available:
        return build_studio_chat_system(
            model_label=route.label or route.model_id,
            api_model=route.model,
            provider_label=provider_display_label(route.provider),
        )
    return build_studio_chat_system(
        model_label="灵枢默认",
        api_model="intent",
        provider_label="系统",
    )


def _model_switch_notice(route: StudioModelRoute | None) -> str:
    """同一会话内切换模型时，避免生成脑沿用历史里的旧模型自称."""
    if not route or not route.available:
        return ""
    label = route.label or route.model_id
    return (
        f"【模型切换说明】本轮由「{label}」作答。"
        "用户可能在同一对话中更换过模型；历史助手消息里自称的模型身份可能已过期，"
        "仅以系统提示中的「当前模型身份」为准，不要沿用历史自称。"
    )


def _prepend_notice(block: str, route: StudioModelRoute | None) -> str:
    notice = _model_switch_notice(route)
    if not notice:
        return block
    if block:
        return f"{notice}\n\n{block}"
    return notice


def _enrich_user_content(
    user_text: str,
    context_block: str,
    *,
    route: StudioModelRoute | None = None,
    analysis: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
) -> str:
    parts: list[str] = []
    notice = _model_switch_notice(route)
    if notice:
        parts.append(notice)
    if context_block:
        parts.append(context_block)
    parts.append(f"当前用户消息：{user_text}")

    if analysis:
        parts.append(f"【Chat Harness 任务分析】\n{json.dumps(analysis, ensure_ascii=False)}")
        for skill in analysis.get("skills") or []:
            hint = studio_skill_hint(str(skill))
            if hint:
                parts.append(f"【技能 · {skill}】{hint}")
        notes = str(analysis.get("notes") or "").strip()
        if notes:
            parts.append(f"【编排提示】{notes}")

    if plan:
        parts.append(f"【回答纲要】\n{json.dumps(plan, ensure_ascii=False)}")

    return "\n\n".join(parts)


async def _build_memory_context(
    bridge: _ModelBridge,
    history: list[dict[str, Any]],
    user_text: str,
    cfg: ChatHarnessConfig,
    route: StudioModelRoute | None,
) -> tuple[str, HarnessPass | None]:
    """有历史时必走小模型记忆提取（答辩核心创新点）."""
    mem_cfg = cfg.memory
    if not mem_cfg.enabled or len(history) < mem_cfg.min_history_messages:
        if history:
            return _prepend_notice(format_history_for_brain(history), route), None
        return "", None

    _, memory = await extract_chat_memory(
        harness_json=bridge.harness_json,
        history=history,
        current_user_text=user_text,
    )
    tail = format_tail_turns(history, max_turns=mem_cfg.tail_raw_turns)
    block = _prepend_notice(format_memory_block(memory, tail), route)

    pass_info = HarnessPass(
        role="memory",
        model=f"role/{mem_cfg.extractor_role}",
        summary=str(memory.get("topic") or "提取对话记忆")[:80],
        detail={
            "referent": memory.get("referent"),
            "key_facts_count": len(memory.get("key_facts") or []),
        },
    )
    return block, pass_info


async def run_chat_harness(
    user_text: str,
    *,
    history: list[dict[str, Any]] | None = None,
    route: StudioModelRoute | None = None,
) -> ChatHarnessResult:
    cfg = load_chat_harness_config()
    hist = history or []
    router = LLMRouter()
    bridge = _ModelBridge(router, route, cfg.analyzer_role)
    system = _build_system(route)

    context_block, memory_pass = await _build_memory_context(bridge, hist, user_text, cfg, route)
    score, strategy = estimate_complexity(user_text, hist, cfg)
    passes: list[HarnessPass] = []
    if memory_pass:
        passes.append(memory_pass)
    passes.append(
        HarnessPass(
            role="router",
            model="heuristic",
            summary=f"复杂度 {score} → 策略 {strategy}",
            detail={"complexity_score": score, "strategy": strategy},
        )
    )

    if not cfg.enabled or strategy == "direct":
        user_content = _enrich_user_content(user_text, context_block, route=route)
        reply = await bridge.generate(system, user_content)
        return ChatHarnessResult(
            reply=reply,
            strategy="direct",
            complexity_score=score,
            model_used=bridge.user_model_label,
            passes=passes,
        )

    analysis: dict[str, Any] = {}
    plan: dict[str, Any] | None = None

    analyze_input = _enrich_user_content(user_text, context_block, route=route)
    try:
        analysis = await bridge.harness_json(STUDIO_ANALYZER_SYSTEM, analyze_input)
    except Exception as exc:
        analysis = {"task_type": "other", "user_goal": user_text[:80], "notes": f"分析跳过: {exc}"}

    passes.append(
        HarnessPass(
            role="analyzer",
            model=f"role/{cfg.analyzer_role}",
            summary=str(analysis.get("user_goal") or "任务分析")[:80],
            detail={"task_type": analysis.get("task_type"), "skills": analysis.get("skills")},
        )
    )

    if strategy == "decompose":
        plan_input = f"用户问题：{user_text}\n\n上下文：{context_block[:3000]}\n\n分析：{json.dumps(analysis, ensure_ascii=False)}"
        try:
            plan = await bridge.harness_json(STUDIO_PLANNER_SYSTEM, plan_input)
        except Exception:
            plan = None
        if plan:
            passes.append(
                HarnessPass(
                    role="planner",
                    model=f"role/{cfg.analyzer_role}",
                    summary=f"拆解 {len(plan.get('outline') or [])} 段",
                    detail={"outline": plan.get("outline")},
                )
            )

    user_content = _enrich_user_content(user_text, context_block, route=route, analysis=analysis, plan=plan)
    draft = await bridge.generate(system, user_content)
    passes.append(
        HarnessPass(
            role="generator",
            model=bridge.user_model_label,
            summary="生成初稿",
            detail={"chars": len(draft)},
        )
    )

    reply = draft
    if cfg.enable_critic and strategy in ("guided", "decompose"):
        critic_input = json.dumps(
            {
                "user_text": user_text,
                "memory_referent": (memory_pass.detail.get("referent") if memory_pass else ""),
                "must_cover": analysis.get("must_cover") or [],
                "assistant_reply": draft[:4000],
            },
            ensure_ascii=False,
        )
        try:
            verdict = await bridge.harness_json(STUDIO_CRITIC_SYSTEM, critic_input)
        except Exception:
            verdict = {"passed": True, "coverage": 100, "issues": []}

        passed = bool(verdict.get("passed", True))
        coverage = int(verdict.get("coverage") or 0)
        issues = verdict.get("issues") or []
        passes.append(
            HarnessPass(
                role="critic",
                model=f"role/{cfg.analyzer_role}",
                summary="质检通过" if passed else f"质检未通过 · 覆盖 {coverage}%",
                detail={"passed": passed, "issues": issues},
            )
        )

        if not passed and cfg.enable_refine and cfg.max_refine_passes > 0 and (issues or verdict.get("refine_hint")):
            refine_user = STUDIO_REFINE_USER_TEMPLATE.format(
                user_text=user_text,
                issues="；".join(str(i) for i in issues) or "答复不完整",
                refine_hint=str(verdict.get("refine_hint") or "补全遗漏要点"),
                draft=draft[:6000],
            )
            if context_block:
                refine_user = f"{context_block}\n\n{refine_user}"
            reply = await bridge.generate(system, refine_user, max_tokens=2560)
            passes.append(
                HarnessPass(
                    role="refiner",
                    model=bridge.user_model_label,
                    summary="根据质检精炼",
                    detail={"chars": len(reply)},
                )
            )

    return ChatHarnessResult(
        reply=reply,
        strategy=strategy,
        complexity_score=score,
        model_used=bridge.user_model_label,
        passes=passes,
    )
