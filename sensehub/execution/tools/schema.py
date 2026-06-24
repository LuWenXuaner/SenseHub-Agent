"""从 TOOL_CATALOG 生成 OpenAI tools JSON Schema."""

from __future__ import annotations

from typing import Any

from sensehub.execution.tools.catalog import TOOL_CATALOG
from sensehub.execution.tools.registry import REGISTRY


def _param_type(spec: str) -> dict[str, Any]:
    s = str(spec).lower().strip()
    if s.startswith("int"):
        return {"type": "integer"}
    if s.startswith("float"):
        return {"type": "number"}
    if s.startswith("bool"):
        return {"type": "boolean"}
    if s.startswith("list"):
        return {"type": "array", "items": {"type": "string"}}
    return {"type": "string"}


def build_openai_tools(*, include: set[str] | None = None) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for name, meta in TOOL_CATALOG.items():
        if name not in REGISTRY:
            continue
        if include and name not in include:
            continue
        params_meta = meta.get("params") or {}
        properties: dict[str, Any] = {}
        required: list[str] = []
        for pname, pspec in params_meta.items():
            key = pname
            optional = "?" in pspec or "=true" in pspec or "=false" in pspec
            clean = pspec.replace("?", "").split("=")[0].strip()
            properties[key] = _param_type(clean)
            if not optional and pname not in ("app",):
                required.append(key)
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": str(meta.get("desc") or name),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }
        )
    tools.append(
        {
            "type": "function",
            "function": {
                "name": "agent_finish",
                "description": "任务完成或无法继续时调用，给出基于已验证工具结果的答复",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {"type": "string", "description": "给用户的最终答复"},
                        "thought": {"type": "string", "description": "简短推理"},
                    },
                    "required": ["answer"],
                },
            },
        }
    )
    return tools
