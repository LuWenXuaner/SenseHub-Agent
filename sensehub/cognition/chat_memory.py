"""灵枢 Chat 对话记忆：小模型提取历史要点 + 近轮原文保留."""

from __future__ import annotations

import json
from typing import Any

from sensehub.cognition.prompts import CHAT_MEMORY_EXTRACTOR_SYSTEM
from sensehub.cognition.session_context import format_history_for_brain


def format_tail_turns(history: list[dict[str, Any]], *, max_turns: int = 2) -> str:
    """保留最近几轮原文，防止记忆摘要丢细节."""
    if max_turns <= 0 or not history:
        return ""
    lines = ["### 最近对话原文（保留细节）"]
    for turn in history[-max_turns:]:
        role = str(turn.get("role", "user")).lower()
        label = "用户" if role == "user" else "助手"
        content = str(turn.get("content", "")).strip()
        if content:
            lines.append(f"{label}：{content}")
    return "\n".join(lines) if len(lines) > 1 else ""


def format_memory_block(memory: dict[str, Any], tail_block: str) -> str:
    """组装交给生成模型的记忆上下文."""
    parts: list[str] = []
    if memory:
        parts.append("### 对话记忆（小模型 Qwen3-8B 提取）")
        parts.append(json.dumps(memory, ensure_ascii=False, indent=2))
        hint = str(memory.get("memory_hint") or "").strip()
        referent = str(memory.get("referent") or "").strip()
        if referent:
            parts.append(f"【指代解析】{referent}")
        if hint:
            parts.append(f"【记忆提示】{hint}")
    if tail_block:
        parts.append(tail_block)
    return "\n\n".join(parts)


async def extract_chat_memory(
    *,
    harness_json,
    history: list[dict[str, Any]],
    current_user_text: str,
) -> tuple[str, dict[str, Any]]:
    """用小模型提取历史记忆，并与近轮原文合并为上下文块."""
    raw = format_history_for_brain(history, max_turns=24)
    if not raw:
        return "", {}

    user_payload = f"{raw}\n\n——\n用户最新消息：{current_user_text}\n\n请提取结构化对话记忆。"
    try:
        memory = await harness_json(CHAT_MEMORY_EXTRACTOR_SYSTEM, user_payload)
    except Exception:
        memory = {
            "topic": "续聊",
            "key_facts": [],
            "conclusions": [],
            "referent": current_user_text[:80],
            "memory_hint": "结合上文理解追问",
        }
    if not isinstance(memory, dict):
        memory = {}
    return raw, memory
