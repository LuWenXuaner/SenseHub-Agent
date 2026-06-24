"""文本规范化与高置信度桌面捷径（match_quick_plan）."""

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
    re.compile(
        r"^打开记事本"
        r"(?:并|,|，)?"
        r"(?:在记事本(?:里|中)?)?"
        r"输入[「」\"']?(.+?)[」」\"']?"
        r"[,，]?\s*并\s*保存"
        r"(?:到[「」\"']?(.+?)[」」\"']?)?$",
        re.I,
    ),
    re.compile(r"^打开记事本(?:并|,|，)?(?:在记事本(?:里|中)?)?输入(.+)$", re.I),
    re.compile(r"^(?:在记事本(?:里|中)?)输入(.+)$", re.I),
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


def _safe_filename_from_content(content: str) -> str:
    stem = re.sub(r'[<>:"/\\|?*\s]+', "_", content.strip())[:32] or "note"
    if not stem.lower().endswith(".txt"):
        stem += ".txt"
    return stem


def _notepad_type_save_plan(content: str, save_hint: str = "") -> ExecutionPlan:
    text = _resolve_type_content(content)
    filename = save_hint.strip() if save_hint else _safe_filename_from_content(text)
    if filename and not filename.lower().endswith(".txt"):
        filename = f"{filename}.txt"
    return ExecutionPlan(
        plan_id=str(uuid.uuid4()),
        summary=f"打开记事本、输入「{text}」并保存",
        steps=[
            PlanStep(
                step_id=1,
                tool="notepad_type_save",
                params={"text": text, "filename": filename, "open": True},
                risk_level="L1",
                description=f"记事本粘贴「{text}」并保存为 {filename}",
            ),
        ],
    )


def _notepad_open_plan() -> ExecutionPlan:
    return ExecutionPlan(
        plan_id=str(uuid.uuid4()),
        summary="打开记事本",
        steps=[
            PlanStep(
                step_id=1,
                tool="open_app",
                params={"name": "notepad", "focus": True},
                risk_level="L1",
                description="打开并置前记事本",
            ),
        ],
    )


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
                description="打开并置前记事本",
            ),
            PlanStep(
                step_id=2,
                tool="type_text",
                params={"text": text},
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


def match_atomic_plan(text: str) -> ExecutionPlan | None:
    """确定性原子工具计划（不经 LLM 逐步选工具）：记事本一条龙等."""
    raw = text.strip().replace("\u3000", " ")

    if "\n" in raw:
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if len(lines) >= 2 and "记事本" in lines[0]:
            joined = " ".join(lines[1:])
            m = re.match(
                r"^(?:在记事本(?:里|中)?)?输入[「」\"']?(.+?)[」」\"']?[,，]?\s*并\s*保存",
                joined,
                re.I,
            )
            if m:
                return _notepad_type_save_plan(m.group(1))

    norm = normalize_intent(raw)
    save_match = _NOTEPAD_TYPE_PATTERNS[0].match(norm)
    if save_match:
        return _notepad_type_save_plan(save_match.group(1), save_match.group(2) or "")

    return None


def match_quick_plan(text: str) -> ExecutionPlan | None:
    """高置信度桌面捷径：命中则跳过 LLM 循环，直接按步骤执行."""
    raw = text.strip().replace("\u3000", " ")

    # 多行须在 normalize 合并空格之前处理
    if "\n" in raw:
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if len(lines) >= 2 and "记事本" in lines[0]:
            joined = " ".join(lines[1:])
            m = re.match(
                r"^(?:在记事本(?:里|中)?)?输入[「」\"']?(.+?)[」」\"']?[,，]?\s*并\s*保存",
                joined,
                re.I,
            )
            if m:
                return _notepad_type_save_plan(m.group(1))
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

    # 带保存的记事本指令优先匹配
    save_match = _NOTEPAD_TYPE_PATTERNS[0].match(text)
    if save_match:
        content = save_match.group(1)
        save_hint = save_match.group(2) or ""
        return _notepad_type_save_plan(content, save_hint)

    for pattern in _NOTEPAD_TYPE_PATTERNS[1:]:
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

    if text in ("打开记事本", "打开 notepad"):
        return _notepad_open_plan()

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

    return None
