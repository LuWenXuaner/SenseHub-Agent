"""从模型正文泄漏的 JSON tool call 修复为结构化调用."""

from __future__ import annotations

import json
import re
from typing import Any

_JSON_BLOCK = re.compile(r"\{[^{}]*\"(?:tool|action)\"[^{}]*\}", re.DOTALL)


def extract_json_tool_call(text: str) -> dict[str, Any] | None:
    raw = text.strip()
    if not raw:
        return None
    if raw.startswith("```"):
        lines = raw.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        raw = "\n".join(lines[1:end]).strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and (obj.get("tool") or obj.get("action")):
            return obj
    except json.JSONDecodeError:
        pass
    m = _JSON_BLOCK.search(raw)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def promote_to_tool_calls(obj: dict[str, Any]) -> tuple[str | None, list[dict[str, Any]]]:
    action = str(obj.get("action", "")).lower().strip()
    if action == "finish" or obj.get("tool") == "agent_finish":
        answer = str(obj.get("answer", "")).strip()
        thought = str(obj.get("thought", "")).strip()
        return answer or thought or "已完成。", []

    tool = str(obj.get("tool", "")).strip()
    if not tool:
        return None, []

    params = obj.get("params") if isinstance(obj.get("params"), dict) else {}
    call_id = "call_repair_1"
    return None, [
        {
            "id": call_id,
            "type": "function",
            "function": {
                "name": tool,
                "arguments": json.dumps(params, ensure_ascii=False),
            },
        }
    ]


def parse_fc_arguments(arguments: str | dict | None) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if not arguments:
        return {}
    try:
        parsed = json.loads(arguments)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}
