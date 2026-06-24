"""从 TOOL_CATALOG 生成 OpenAI tools JSON Schema，并做参数校验."""

from __future__ import annotations

from typing import Any

from sensehub.execution.tools.catalog import TOOL_CATALOG
from sensehub.execution.tools.registry import REGISTRY

_TYPE_LABELS = ("int", "float", "bool", "str", "list")


def _strip_spec(spec: str) -> tuple[str, bool]:
    s = str(spec).strip()
    optional = "?" in s
    s = s.replace("?", "").strip()
    return s, optional


def _split_default(spec: str) -> tuple[str, str | None]:
    if "=" not in spec:
        return spec.strip(), None
    left, _, right = spec.partition("=")
    return left.strip(), right.strip()


def _infer_schema(base_spec: str) -> dict[str, Any]:
    low = base_spec.lower()
    if low.startswith("list"):
        return {"type": "array", "items": {"type": "string"}}
    if low.startswith("int"):
        return {"type": "integer"}
    if low.startswith("float"):
        return {"type": "number"}
    if low.startswith("bool"):
        return {"type": "boolean"}
    if "|" in base_spec and not any(low.startswith(t) for t in _TYPE_LABELS):
        enums = [x.strip() for x in base_spec.split("|") if x.strip()]
        if enums:
            return {"type": "string", "enum": enums}
    return {"type": "string"}


def _param_schema(spec: str) -> tuple[dict[str, Any], bool]:
    clean, optional_mark = _strip_spec(spec)
    base, default = _split_default(clean)
    schema = _infer_schema(base)
    if default is not None and schema.get("type") == "string":
        schema["default"] = default
    optional = optional_mark or default is not None
    return schema, optional


def build_openai_tools(
    *,
    include: set[str] | None = None,
    ordered_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    ordered = [n for n in (ordered_names or []) if n in TOOL_CATALOG]
    for name in TOOL_CATALOG.keys():
        if name not in ordered:
            ordered.append(name)

    for name in ordered:
        meta = TOOL_CATALOG.get(name) or {}
        if name not in REGISTRY:
            continue
        if include and name not in include:
            continue
        params_meta = meta.get("params") or {}
        properties: dict[str, Any] = {}
        required: list[str] = []
        for pname, pspec in params_meta.items():
            schema, optional = _param_schema(str(pspec))
            properties[pname] = schema
            if not optional:
                required.append(pname)
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


def validate_tool_params(tool: str, params: dict[str, Any]) -> str | None:
    """校验参数是否符合 TOOL_CATALOG 声明，失败返回可读错误."""
    meta = TOOL_CATALOG.get(tool)
    if not meta:
        return None
    spec_map = meta.get("params") or {}
    if not isinstance(params, dict):
        return "params 必须是 object"

    unknown = [k for k in params.keys() if k not in spec_map]
    if unknown:
        return f"参数不支持: {', '.join(unknown)}"

    for key, raw_spec in spec_map.items():
        schema, optional = _param_schema(str(raw_spec))
        if key not in params:
            if optional:
                continue
            return f"缺少必填参数: {key}"
        value = params[key]
        typ = schema.get("type")
        if typ == "integer" and not isinstance(value, int):
            return f"参数 {key} 需为 int"
        if typ == "number" and not isinstance(value, (int, float)):
            return f"参数 {key} 需为 number"
        if typ == "boolean" and not isinstance(value, bool):
            return f"参数 {key} 需为 bool"
        if typ == "array":
            if not isinstance(value, list):
                return f"参数 {key} 需为 list"
            if not all(isinstance(x, str) for x in value):
                return f"参数 {key} 需为 list[str]"
        if typ == "string" and not isinstance(value, str):
            return f"参数 {key} 需为 str"
        enum = schema.get("enum")
        if enum and isinstance(value, str) and value not in enum:
            return f"参数 {key} 仅支持: {' | '.join(enum)}"

    one_of = meta.get("one_of")
    if isinstance(one_of, list) and one_of:
        ok = False
        for group in one_of:
            if not isinstance(group, list) or not group:
                continue
            if all(k in params and params.get(k) not in (None, "", []) for k in group):
                ok = True
                break
        if not ok:
            options: list[str] = []
            for group in one_of:
                if isinstance(group, list) and group:
                    options.append("+".join(group))
            if options:
                return f"参数需满足其一: {', '.join(options)}"
    return None
