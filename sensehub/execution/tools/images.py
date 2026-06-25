"""图片搜索与下载（HTTP，不依赖 Playwright）."""

from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from sensehub.security.sandbox import check_filesystem, default_save_dir

_HTTP_TIMEOUT = 20
_MAX_IMAGE_BYTES = 12 * 1024 * 1024
_MAX_SEARCH_HTML_BYTES = 768_000
_BING_IMG_MURL_RE = re.compile(
    r'(?:murl&quot;:&quot;|\"murl\"\s*:\s*\")(https?://[^\"&\\]+)',
    re.I,
)
_IMG_EXT_BY_MAGIC: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
]
_EXT_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}


def _guess_ext(data: bytes, content_type: str, url: str) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in _EXT_BY_CONTENT_TYPE:
        return _EXT_BY_CONTENT_TYPE[ct]
    for magic, ext in _IMG_EXT_BY_MAGIC:
        if data.startswith(magic):
            return ext
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    path = urllib.parse.urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
        if path.endswith(ext):
            return ext if ext != ".jpeg" else ".jpg"
    return ".jpg"


def _safe_stem(text: str) -> str:
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text.strip())[:48]
    return stem or "image"


def _resolve_image_path(params: dict[str, Any], *, default_name: str) -> Path:
    raw = str(params.get("path") or params.get("filename") or default_name).strip()
    if not raw:
        raw = default_name
    target = Path(raw)
    if not target.is_absolute():
        target = (default_save_dir() / target.name).resolve()
    else:
        target = target.expanduser().resolve()
    decision = check_filesystem(str(target), "write")
    if not decision.allowed:
        raise PermissionError(f"{decision.user_message} {decision.grant_hint}")
    return Path(decision.resolved_path)


def _http_get_bytes(url: str, *, accept: str, max_bytes: int) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SenseHub-Agent/1.0 (image tool)",
            "Accept": accept,
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT, context=ctx) as resp:
        data = resp.read(max_bytes + 1)
    if len(data) > max_bytes:
        data = data[:max_bytes]
    return data


def _bing_image_search(query: str, max_results: int) -> list[dict[str, str]]:
    q = urllib.parse.quote(query)
    url = f"https://www.bing.com/images/search?q={q}&form=HDRSC2&first=1"
    body = _http_get_bytes(url, accept="text/html,image/*,*/*", max_bytes=_MAX_SEARCH_HTML_BYTES)
    html = body.decode("utf-8", errors="replace")
    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for m in _BING_IMG_MURL_RE.finditer(html):
        img_url = m.group(1).replace("\\/", "/").strip()
        if not img_url.startswith("http") or img_url in seen:
            continue
        seen.add(img_url)
        rows.append(
            {
                "url": img_url,
                "title": query,
                "source": "bing_images",
            }
        )
        if len(rows) >= max_results:
            break
    return rows


def search_images(params: dict[str, Any]) -> dict[str, Any]:
    """搜索网络图片，返回直链 URL 列表."""
    query = str(params.get("query") or "").strip()
    if not query:
        raise ValueError("query 不能为空")
    max_results = max(1, min(int(params.get("max_results", 8)), 12))
    rows = _bing_image_search(query, max_results)
    if not rows:
        raise RuntimeError(f"未找到与「{query}」相关的图片")
    return {
        "query": query,
        "count": len(rows),
        "images": rows,
        "source": "bing_images",
    }


def _download_image_bytes(url: str) -> tuple[bytes, str]:
    if not url.startswith(("http://", "https://")):
        raise ValueError("url 须为 http(s) 地址")
    body = _http_get_bytes(url, accept="image/*,*/*", max_bytes=_MAX_IMAGE_BYTES)
    if len(body) < 128:
        raise ValueError("响应过短，可能不是有效图片")
    content_type = ""
    return body, content_type


def download_image(params: dict[str, Any]) -> dict[str, Any]:
    """从图片 URL 下载到本地（默认用户保存目录）."""
    url = str(params.get("url") or "").strip()
    if not url:
        raise ValueError("url 不能为空")
    default_name = f"{_safe_stem(Path(urllib.parse.urlparse(url).path).stem or 'image')}.jpg"
    body, _ = _download_image_bytes(url)
    ext = _guess_ext(body, "", url)
    target = _resolve_image_path(params, default_name=_safe_stem(default_name) + ext)
    if target.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
        target = target.with_suffix(ext)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    return {
        "url": url,
        "path": str(target),
        "filename": target.name,
        "bytes": len(body),
        "content_type": f"image/{target.suffix.lstrip('.')}",
    }


def search_and_download_image(params: dict[str, Any]) -> dict[str, Any]:
    """搜索图片并下载一张；可选同时用 Edge 打开搜索页."""
    query = str(params.get("query") or "").strip()
    if not query:
        raise ValueError("query 不能为空")
    index = max(0, int(params.get("index", 0)))
    open_browser = bool(params.get("open_browser", False))

    search_out = search_images({"query": query, "max_results": max(index + 1, 6)})
    images = search_out.get("images") or []
    if index >= len(images):
        raise RuntimeError(f"仅有 {len(images)} 张候选图，index={index} 超出范围")

    browser_out = None
    if open_browser:
        from sensehub.execution.tools.browser import web_search

        browser_out = web_search({"query": query})

    picked = images[index]
    img_url = str(picked.get("url") or "")
    stem = _safe_stem(query)
    filename = str(params.get("filename") or f"{stem}.jpg").strip()
    dl = download_image({"url": img_url, "filename": filename})

    return {
        "query": query,
        "picked_index": index,
        "image_url": img_url,
        "saved_path": dl.get("path"),
        "filename": dl.get("filename"),
        "bytes": dl.get("bytes"),
        "search_count": search_out.get("count"),
        "open_browser": open_browser,
        "browser": browser_out,
    }
