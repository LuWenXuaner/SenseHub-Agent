"""使用 Microsoft Edge 打开搜索页."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from sensehub.settings import get_settings

_EDGE_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


def _resolve_edge() -> Path:
    settings = get_settings()
    custom = settings.edge_path.strip() if settings.edge_path else ""
    if custom:
        p = Path(custom)
        if p.exists():
            return p

    for candidate in _EDGE_CANDIDATES:
        p = Path(candidate)
        if p.exists():
            return p

    raise FileNotFoundError(
        "未找到 Microsoft Edge，请在 config/local.env 设置 EDGE_PATH"
    )


def web_search(params: dict[str, Any]) -> dict[str, Any]:
    query = params.get("query", "")
    if not query:
        raise ValueError("query 不能为空")

    if sys.platform != "win32":
        raise RuntimeError("web_search 当前仅支持 Windows + Edge")

    # Windows/Edge 约定："? 关键词" 走浏览器里已设置的默认搜索引擎
    search_arg = f"? {query.strip()}"

    edge = _resolve_edge()
    proc = subprocess.Popen(
        [str(edge), "--new-window", search_arg],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
    )
    time.sleep(0.8)
    code = proc.poll()
    if code is not None and code != 0:
        raise RuntimeError(f"Edge 启动失败，退出码 {code}")

    return {
        "query": query,
        "search": search_arg,
        "method": "edge-default-search",
        "browser": str(edge),
        "pid": proc.pid,
    }


def open_url(params: dict[str, Any]) -> dict[str, Any]:
    url = str(params.get("url", "")).strip()
    if not url:
        raise ValueError("url 不能为空")
    if not url.startswith(("http://", "https://", "file://")):
        url = "https://" + url

    if sys.platform != "win32":
        raise RuntimeError("open_url 当前仅支持 Windows + Edge")

    edge = _resolve_edge()
    proc = subprocess.Popen(
        [str(edge), "--new-window", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
    )
    time.sleep(0.5)
    return {"url": url, "browser": str(edge), "pid": proc.pid}
