"""Playwright 浏览器自动化（Windows snapshot-act）."""

from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()
_playwright = None
_browser = None
_context = None
_page = None


def _ensure_page():
    global _playwright, _browser, _context, _page
    with _lock:
        if _page is not None:
            try:
                if not _page.is_closed():
                    return _page
            except Exception:
                _page = None
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("未安装 playwright，请运行: playwright install chromium") from exc
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=False)
        _context = _browser.new_context()
        _page = _context.new_page()
        return _page


def browser_status(params: dict[str, Any]) -> dict[str, Any]:
    _ = params
    try:
        page = _ensure_page()
        return {
            "ready": True,
            "url": page.url,
            "title": page.title(),
        }
    except Exception as exc:
        return {"ready": False, "error": str(exc)}


def browser_navigate(params: dict[str, Any]) -> dict[str, Any]:
    url = str(params.get("url", "")).strip()
    if not url:
        raise ValueError("url 不能为空")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    page = _ensure_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    return {"url": page.url, "title": page.title()}


def _snapshot_elements(page) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    elements = page.query_selector_all(
        "a, button, input, textarea, select, [role=button], [role=link], [role=textbox]"
    )
    for i, el in enumerate(elements[:80]):
        try:
            tag = el.evaluate("el => el.tagName.toLowerCase()")
            text = (el.inner_text() or "")[:80].strip()
            placeholder = el.get_attribute("placeholder") or ""
            name = el.get_attribute("name") or ""
            aria = el.get_attribute("aria-label") or ""
            label = text or placeholder or aria or name or tag
            refs.append({"ref": f"e{i}", "tag": tag, "label": label})
        except Exception:
            continue
    return refs


def browser_snapshot(params: dict[str, Any]) -> dict[str, Any]:
    page = _ensure_page()
    refs = _snapshot_elements(page)
    shot = None
    if params.get("screenshot", True):
        from sensehub.settings import get_settings

        settings = get_settings()
        path = settings.screenshots_dir / f"browser_{int(__import__('time').time())}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path))
        shot = str(path)
    return {
        "url": page.url,
        "title": page.title(),
        "refs": refs,
        "ref_count": len(refs),
        "screenshot_path": shot,
    }


def browser_act(params: dict[str, Any]) -> dict[str, Any]:
    action = str(params.get("action", "click")).lower()
    ref = str(params.get("ref", "")).strip()
    value = params.get("value", "")
    page = _ensure_page()
    refs = _snapshot_elements(page)
    target = next((r for r in refs if r["ref"] == ref), None)
    if not target:
        raise RuntimeError(f"无效 ref: {ref}，请先 browser_snapshot")
    idx = int(ref[1:])
    el = page.query_selector_all(
        "a, button, input, textarea, select, [role=button], [role=link], [role=textbox]"
    )[idx]
    if action == "click":
        el.click()
    elif action == "fill":
        el.fill(str(value))
    elif action == "press":
        el.press(str(value or "Enter"))
    else:
        raise ValueError(f"不支持 action: {action}")
    return {"action": action, "ref": ref, "label": target.get("label"), "url": page.url}


def browser_tabs(params: dict[str, Any]) -> dict[str, Any]:
    _ = params
    page = _ensure_page()
    return {"count": 1, "active": {"url": page.url, "title": page.title()}}
