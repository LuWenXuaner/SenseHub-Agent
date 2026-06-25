"""增强文件管理：移动、重命名、删除、搜索、信息查询."""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from sensehub.execution.tools.base import tool_result
from sensehub.security.sandbox import assert_filesystem, check_filesystem, workspace_dir


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
        try:
            stat = item.stat()
            entries.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "path": str(item),
                "size_bytes": stat.st_size,
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            })
        except OSError:
            entries.append({"name": item.name, "type": "dir" if item.is_dir() else "file", "path": str(item)})
    return tool_result(True, data={"path": str(path), "entries": entries, "count": len(entries)})


def read_file(params: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_safe(params["path"])
    max_bytes = int(params.get("max_bytes", 65536))
    data = path.read_bytes()[:max_bytes]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    return tool_result(True, data={
        "path": str(path),
        "content": text,
        "truncated": path.stat().st_size > max_bytes,
        "size_bytes": path.stat().st_size,
    })


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
    return tool_result(True, f"已写入 {len(content.encode('utf-8'))} 字节到 {path}", data={
        "path": str(path), "bytes": len(content.encode("utf-8")), "append": append,
    })


def move_file(params: dict[str, Any]) -> dict[str, Any]:
    src = _resolve_safe(params["src"])
    dst = _resolve_safe(params["dst"], write=True)
    if not src.exists():
        raise FileNotFoundError(f"源路径不存在: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    result_path = dst if dst.is_dir() else dst
    shutil.move(str(src), str(result_path))
    return tool_result(True, f"已移动 {src} -> {result_path}", data={"src": str(src), "dst": str(result_path)})


def rename_file(params: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_safe(params["path"], write=True)
    new_name = str(params.get("new_name", "")).strip()
    if not new_name:
        raise ValueError("new_name 不能为空")
    if not path.exists():
        raise FileNotFoundError(f"路径不存在: {path}")
    new_path = path.parent / new_name
    if new_path.exists():
        raise FileExistsError(f"目标已存在: {new_path}")
    path.rename(new_path)
    return tool_result(True, f"已重命名 {path.name} -> {new_name}", data={"old": str(path), "new": str(new_path)})


def copy_file(params: dict[str, Any]) -> dict[str, Any]:
    src = _resolve_safe(params["src"])
    dst = _resolve_safe(params["dst"], write=True)
    if not src.is_file():
        raise FileNotFoundError(str(src))
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return tool_result(True, f"已复制 {src} -> {dst}", data={"src": str(src), "dst": str(dst)})


def delete_file(params: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_safe(params["path"], write=True)
    if not path.exists():
        raise FileNotFoundError(f"路径不存在: {path}")
    is_dir = path.is_dir()
    if is_dir:
        shutil.rmtree(path)
    else:
        path.unlink()
    return tool_result(True, f"已删除 {'目录' if is_dir else '文件'}: {path}", data={"path": str(path), "type": "dir" if is_dir else "file"})


def search_files(params: dict[str, Any]) -> dict[str, Any]:
    pattern = str(params.get("pattern", "*")).strip()
    search_path = params.get("path", ".")
    recursive = bool(params.get("recursive", True))
    max_results = int(params.get("max_results", 100))

    root = _resolve_safe(search_path)
    if not root.is_dir():
        raise NotADirectoryError(str(root))

    results: list[dict[str, Any]] = []
    glob_fn = root.rglob if recursive else root.glob
    for item in glob_fn(pattern):
        try:
            stat = item.stat()
            results.append({
                "name": item.name,
                "path": str(item),
                "type": "dir" if item.is_dir() else "file",
                "size_bytes": stat.st_size,
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            })
        except OSError:
            results.append({"name": item.name, "path": str(item), "type": "dir" if item.is_dir() else "file"})
        if len(results) >= max_results:
            break

    return tool_result(True, data={
        "pattern": pattern,
        "root": str(root),
        "results": results,
        "count": len(results),
        "truncated": len(results) >= max_results,
    })


def file_exists(params: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_safe(params["path"])
    return tool_result(True, data={
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    })


def get_file_info(params: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_safe(params["path"])
    if not path.exists():
        raise FileNotFoundError(str(path))
    stat = path.stat()
    is_dir = path.is_dir()
    return tool_result(True, data={
        "name": path.name,
        "path": str(path),
        "type": "dir" if is_dir else "file",
        "size_bytes": stat.st_size,
        "size_display": _format_size(stat.st_size),
        "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime)),
        "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
        "parent": str(path.parent),
        "extension": path.suffix,
        "stem": path.stem,
    })


def ensure_directory(params: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_safe(params["path"], write=True)
    path.mkdir(parents=True, exist_ok=True)
    return tool_result(True, f"已确保目录存在: {path}", data={"path": str(path)})


def open_folder(params: dict[str, Any]) -> dict[str, Any]:
    import subprocess
    path = _resolve_safe(params.get("path", "."))
    if not path.exists():
        raise FileNotFoundError(str(path))
    subprocess.Popen(["explorer", str(path)], shell=False)
    return tool_result(True, f"已打开文件夹: {path}", data={"opened": str(path)})


def _format_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
