"""文件操作（沙箱路径解析与权限）."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from sensehub.security.sandbox import assert_filesystem, check_filesystem


def _resolve_safe(path_str: str, *, write: bool = False) -> Path:
    op = "write" if write else "read"
    return assert_filesystem(path_str, op)


def list_dir(params: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_safe(params.get("path", "."))
    if not path.is_dir():
        raise NotADirectoryError(str(path))
    limit = int(params.get("limit", 100))
    entries = []
    for item in sorted(path.iterdir())[:limit]:
        entries.append(
            {
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "path": str(item),
            }
        )
    return {"path": str(path), "entries": entries, "count": len(entries)}


def read_file(params: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_safe(params["path"])
    max_bytes = int(params.get("max_bytes", 65536))
    data = path.read_bytes()[:max_bytes]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    return {"path": str(path), "content": text, "truncated": path.stat().st_size > max_bytes}


def write_file(params: dict[str, Any]) -> dict[str, Any]:
    decision = check_filesystem(params["path"], "write")
    if not decision.allowed:
        raise PermissionError(f"{decision.user_message} {decision.grant_hint}")
    path = Path(decision.resolved_path)
    content = params.get("content", "")
    append = bool(params.get("append"))
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as f:
        f.write(content)
    return {"path": str(path), "bytes": len(content.encode("utf-8")), "append": append}


def copy_file(params: dict[str, Any]) -> dict[str, Any]:
    src = _resolve_safe(params["src"])
    dst = _resolve_safe(params["dst"], write=True)
    if not src.is_file():
        raise FileNotFoundError(str(src))
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {"src": str(src), "dst": str(dst)}


def file_exists(params: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_safe(params["path"])
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
    }


def open_folder(params: dict[str, Any]) -> dict[str, Any]:
    import subprocess

    path = _resolve_safe(params.get("path", "."))
    if not path.exists():
        raise FileNotFoundError(str(path))
    subprocess.Popen(["explorer", str(path)], shell=False)
    return {"opened": str(path)}
