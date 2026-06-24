"""文本规范化（供规划脑使用）。match_quick_plan 已废弃，主路径一律走 orchestrate_brains."""

from __future__ import annotations

import re
import uuid

from sensehub.models.schemas import ExecutionPlan, PlanStep

_SEARCH_PATTERNS = [
    re.compile(r"^(?:打开浏览器搜索|在浏览器中搜索|用浏览器搜索|浏览器搜索)\s*(.+)$", re.I),
    re.compile(r"^(?:打开浏览器搜索|在浏览器中搜索)(.+)$", re.I),
    re.compile(r"^(?:搜索|帮我搜索|查一下)\s*(.+)$", re.I),
]

_NOTEPAD_TYPE_PATTERNS = [
    re.compile(r"^打开记事本(?:并|,|，)?(?:在记事本(?:里|中)?)?输入(.+)$", re.I),
    re.compile(r"^(?:在记事本(?:里|中)?)输入(.+)$", re.I),
    re.compile(r"^打开记事本$", re.I),
]

_GUI_PATTERNS = [
    re.compile(r"^(?:看屏幕|根据屏幕|屏幕操作|看下屏幕|看着屏幕|用屏幕)(.+)$", re.I),
    re.compile(r"^vlm\s*(.+)$", re.I),
]


def _gui_agent_plan(intent: str) -> ExecutionPlan:
    intent = intent.strip()
    return ExecutionPlan(
        plan_id=str(uuid.uuid4()),
        summary=f"VLM 屏幕操作: {intent}",
        steps=[
            PlanStep(
                step_id=1,
                tool="gui_agent",
                params={"intent": intent, "max_steps": 10},
                risk_level="L1",
                description=f"看屏幕执行：{intent}",
            )
        ],
    )


_VAGUE_TYPE_CONTENT = frozenset(
    {"几个字", "一些字", "点字", "些文字", "文字", "点东西", "一些文字", "随便几个字"}
)


def _resolve_type_content(raw: str) -> str:
    content = raw.strip().strip("「」\"'")
    if not content or content in _VAGUE_TYPE_CONTENT:
        return "灵枢 Agent 测试"
    return content


def _notepad_type_plan(content: str) -> ExecutionPlan:
    text = _resolve_type_content(content)
    return ExecutionPlan(
        plan_id=str(uuid.uuid4()),
        summary=f"打开记事本并输入：{text}",
        steps=[
            PlanStep(
                step_id=1,
                tool="open_app",
                params={"name": "notepad", "focus": True},
                risk_level="L1",
                description="打开并聚焦记事本",
            ),
            PlanStep(
                step_id=2,
                tool="type_text",
                params={"text": text, "app": "notepad"},
                risk_level="L1",
                description=f"在记事本中输入「{text}」",
            ),
        ],
    )


def normalize_intent(text: str) -> str:
    text = text.strip().replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def _search_plan(query: str) -> ExecutionPlan:
    query = query.strip()
    return ExecutionPlan(
        plan_id=str(uuid.uuid4()),
        summary=f"浏览器搜索: {query}",
        steps=[
            PlanStep(
                step_id=1,
                tool="web_search",
                params={"query": query},
                risk_level="L1",
                description=f"使用 Edge 搜索「{query}」",
            )
        ],
    )


def match_quick_plan(text: str) -> ExecutionPlan | None:
    """已废弃：执行捷径不再接入主路径，仅保留供单元测试对照。"""
    raw = text.strip().replace("\u3000", " ")

    # 多行须在 normalize 合并空格之前处理
    if "\n" in raw:
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if len(lines) >= 2 and "记事本" in lines[0]:
            joined = " ".join(lines[1:])
            m = re.match(r"^(?:在记事本(?:里|中)?)?输入(.+)$", joined, re.I)
            if m:
                return _notepad_type_plan(m.group(1))
            if "输入" in joined:
                return _notepad_type_plan("几个字")

    text = normalize_intent(raw)

    for pattern in _GUI_PATTERNS:
        m = pattern.match(text)
        if m and m.group(1).strip():
            return _gui_agent_plan(m.group(1))

    for pattern in _NOTEPAD_TYPE_PATTERNS[:2]:
        m = pattern.match(text)
        if m:
            return _notepad_type_plan(m.group(1))

    if re.match(r"^(截个?图|截图|截屏|screenshot)$", text, re.I):
        return ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            summary="截取全屏",
            steps=[
                PlanStep(
                    step_id=1,
                    tool="screenshot",
                    params={"mode": "fullscreen"},
                    risk_level="L1",
                    description="截取全屏",
                )
            ],
        )

    if text in ("打开记事本", "打开 notepad") or re.match(r"^打开记事本(?:并|,|，)?", text, re.I):
        return _gui_agent_plan("打开记事本并激活到前台最前，确保窗口可见")

    if re.match(r"^关闭记事本", text, re.I):
        return _gui_agent_plan("关闭记事本窗口")

    if re.match(r"^(?:关闭|关掉|退出)\s*(.+)$", text, re.I):
        target = re.sub(r"^(?:关闭|关掉|退出)\s*", "", text, flags=re.I).strip()
        if target:
            return _gui_agent_plan(f"关闭或退出：{target}")

    if text in ("待确认测试", "L2测试"):
        return ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            summary="L2 待确认冒烟测试",
            steps=[
                PlanStep(
                    step_id=1,
                    tool="screenshot",
                    params={"mode": "fullscreen"},
                    risk_level="L2",
                    requires_confirm=True,
                    description="截取全屏（需人工确认）",
                )
            ],
        )

    for pattern in _SEARCH_PATTERNS:
        m = pattern.match(text)
        if m and m.group(1).strip():
            return _search_plan(m.group(1))

    if should_use_gui_agent(text):
        return _gui_agent_plan(text)

    return None
