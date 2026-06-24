"""通用沙箱：文件系统权限、可写范围、拒绝时给出客户可理解的授权指引."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from sensehub.settings import get_settings

Operation = Literal["read", "write", "list"]
_GRANTS_FILE = "sandbox_grants.json"


@dataclass(frozen=True)
class SandboxDecision:
    allowed: bool
    resolved_path: str
    operation: str
    scope: str
    user_message: str
    grant_hint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "path": self.resolved_path,
            "operation": self.operation,
            "scope": self.scope,
            "user_message": self.user_message,
            "grant_hint": self.grant_hint,
        }


def workspace_dir() -> Path:
    settings = get_settings()
    data_root = settings.paths.get("data", {}).get("root") or settings.data_root
    base = Path(data_root) if data_root else Path.home() / "SenseHubData"
    ws = base / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws.resolve()


def _policy_whitelist() -> list[Path]:
    policies = get_settings().policies.get("execution", {})
    dirs = policies.get("file_whitelist_dirs") or []
    roots: list[Path] = []
    for raw in dirs:
        try:
            p = Path(str(raw)).expanduser().resolve()
            p.mkdir(parents=True, exist_ok=True)
            roots.append(p)
        except OSError:
            continue
    return roots


def _runtime_grants() -> list[Path]:
    settings = get_settings()
    data_root = settings.paths.get("data", {}).get("root") or settings.data_root
    if not data_root:
        return []
    grant_path = Path(data_root) / _GRANTS_FILE
    if not grant_path.exists():
        return []
    try:
        data = json.loads(grant_path.read_text(encoding="utf-8"))
        paths = data.get("paths", []) if isinstance(data, dict) else []
    except json.JSONDecodeError:
        return []
    roots: list[Path] = []
    for raw in paths:
        try:
            roots.append(Path(str(raw)).expanduser().resolve())
        except OSError:
            continue
    return roots


def add_runtime_grant(path_str: str) -> Path:
    """用户确认后追加可写路径（会话外持久化）."""
    p = Path(path_str).expanduser().resolve()
    settings = get_settings()
    data_root = Path(settings.paths.get("data", {}).get("root") or settings.data_root)
    data_root.mkdir(parents=True, exist_ok=True)
    grant_path = data_root / _GRANTS_FILE
    existing = []
    if grant_path.exists():
        try:
            data = json.loads(grant_path.read_text(encoding="utf-8"))
            existing = list(data.get("paths", [])) if isinstance(data, dict) else []
        except json.JSONDecodeError:
            existing = []
    normalized = str(p)
    if normalized not in existing:
        existing.append(normalized)
    grant_path.write_text(json.dumps({"paths": existing}, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def writable_roots() -> list[Path]:
    roots = [workspace_dir(), *_policy_whitelist(), *_runtime_grants()]
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        key = str(r).lower()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def readable_roots() -> list[Path]:
    settings = get_settings()
    roots = writable_roots()
    roots.append(Path.home().resolve())
    shots = settings.screenshots_dir
    if shots:
        roots.append(Path(shots).resolve())
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        key = str(r).lower()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _in_roots(path: Path, roots: list[Path]) -> Path | None:
    for root in roots:
        try:
            path.relative_to(root)
            return root
        except ValueError:
            continue
    return None


def resolve_path(path_str: str) -> Path:
    if not path_str or not str(path_str).strip():
        raise ValueError("path 不能为空")
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = (workspace_dir() / p).resolve()
    else:
        p = p.resolve()
    return p


def check_filesystem(path_str: str, operation: Operation = "read") -> SandboxDecision:
    try:
        path = resolve_path(path_str)
    except ValueError as exc:
        return SandboxDecision(
            allowed=False,
            resolved_path=path_str,
            operation=operation,
            scope="invalid",
            user_message=str(exc),
            grant_hint="请提供有效的文件或文件夹路径",
        )

    roots = writable_roots() if operation == "write" else readable_roots()
    matched = _in_roots(path, roots)
    if matched:
        scope = "workspace" if matched == workspace_dir() else "policy" if matched in _policy_whitelist() else "grant"
        if matched == Path.home().resolve() and operation == "write":
            pass  # home write not in writable_roots
        else:
            return SandboxDecision(
                allowed=True,
                resolved_path=str(path),
                operation=operation,
                scope=scope if scope != "grant" or matched in _runtime_grants() else "policy",
                user_message="",
                grant_hint="",
            )

    ws = workspace_dir()
    hint = (
        f"当前可在沙箱工作区「{ws}」及已授权目录内{('写入' if operation == 'write' else '访问')}。"
        f"如需访问「{path}」，请在对话中确认授权，或前往「安全中心」添加目录白名单。"
    )
    return SandboxDecision(
        allowed=False,
        resolved_path=str(path),
        operation=operation,
        scope="denied",
        user_message=f"沙箱未授权该路径：{path}",
        grant_hint=hint,
    )


def assert_filesystem(path_str: str, operation: Operation = "read") -> Path:
    decision = check_filesystem(path_str, operation)
    if not decision.allowed:
        raise PermissionError(f"{decision.user_message} {decision.grant_hint}")
    return Path(decision.resolved_path)


def path_needs_confirm(path_str: str, operation: Operation = "write") -> bool:
    """工作区外写入须用户点确认."""
    if operation != "write":
        return False
    try:
        path = resolve_path(path_str)
    except ValueError:
        return True
    ws = workspace_dir()
    try:
        path.relative_to(ws)
        return False
    except ValueError:
        return True


def grant_paths_on_confirm(steps: list[Any]) -> list[str]:
    """用户点确认后，为计划中的工作区外写入路径追加运行时授权."""
    granted: list[str] = []
    write_tools = {"write_file", "copy_file"}
    for step in steps:
        tool = getattr(step, "tool", None) or (step.get("tool") if isinstance(step, dict) else "")
        params = getattr(step, "params", None) or (step.get("params") if isinstance(step, dict) else {}) or {}
        if tool not in write_tools:
            continue
        path_key = "path" if tool == "write_file" else "dst"
        target = str(params.get(path_key, ""))
        if not target or not path_needs_confirm(target, "write"):
            continue
        try:
            path = resolve_path(target)
            grant_target = path if path.is_dir() else path.parent
            resolved = add_runtime_grant(str(grant_target))
            granted.append(str(resolved))
        except (ValueError, OSError):
            continue
    return granted


def describe_for_planner() -> str:
    ws = workspace_dir()
    writable = writable_roots()
    lines = [
        "\n### 沙箱与权限（通用规则，禁止为单个案例写死逻辑）",
        f"- 默认工作区（可自由读写）：{ws}",
        "- 相对路径均解析到工作区下",
        "- 工作区外写入：步骤须标记 risk_level=L2 且 requires_confirm=true，等用户点「确认」",
        "- 无专用工具时：可组合 open_app / web_search / open_url / gui_agent / fetch_url 等迂回完成目标",
        "- 需要文件结果：优先 write_file 到工作区，再把路径告诉用户",
        "已授权可写目录：",
    ]
    for r in writable:
        lines.append(f"  - {r}")
    lines.append("- 若路径未授权，应规划到工作区，或拆成「先请求用户授权再执行」的步骤")
    return "\n".join(lines)


def status_payload() -> dict[str, Any]:
    return {
        "workspace": str(workspace_dir()),
        "writable_roots": [str(p) for p in writable_roots()],
        "readable_roots": [str(p) for p in readable_roots()],
        "runtime_grants": [str(p) for p in _runtime_grants()],
        "policy_whitelist": [str(p) for p in _policy_whitelist()],
    }
