"""增强 Playwright 浏览器自动化：多标签页、IFrame、弹窗拦截、等待."""

from __future__ import annotations

import threading
from typing import Any

from sensehub.execution.tools.base import push_progress, tool_result, safe_execute

_lock = threading.Lock()
_playwright = None
_browser = None
_context = None
_pages: list = []  # 多标签页


def _ensure_page():
    global _playwright, _browser, _context, _pages
    with _lock:
        if _pages:
            active = [p for p in _pages if not p.is_closed()]
            if active:
                _pages = active
                return active[-1]  # 最近使用的标签页
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("未安装 playwright，请运行: playwright install chromium") from exc
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=False)
        _context = _browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        )
        # 全局弹窗自动确认
        _context.set_default_timeout(30000)
        page = _context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())
        _pages = [page]
        return page


def _active_page():
    pages = [p for p in _pages if not p.is_closed()]
    if pages:
        return pages[-1]
    return _ensure_page()


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


def browser_status(params: dict[str, Any]) -> dict[str, Any]:
    _ = params
    try:
        page = _active_page()
        return tool_result(True, data={
            "ready": True,
            "url": page.url,
            "title": page.title(),
            "tab_count": len([p for p in _pages if not p.is_closed()]),
        })
    except Exception as exc:
        return tool_result(False, str(exc), data={"ready": False}, error=str(exc))


def browser_navigate(params: dict[str, Any]) -> dict[str, Any]:
    url = str(params.get("url", "")).strip()
    if not url:
        raise ValueError("url 不能为空")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    wait_until = str(params.get("wait_until", "domcontentloaded"))
    timeout = int(params.get("timeout", 60000))

    page = _active_page()
    push_progress(f"正在打开 {url}...")
    page.goto(url, wait_until=wait_until, timeout=timeout)
    return tool_result(True, f"已打开: {page.url}", data={"url": page.url, "title": page.title()})


def browser_snapshot(params: dict[str, Any]) -> dict[str, Any]:
    page = _active_page()
    refs = _snapshot_elements(page)
    shot = None
    if params.get("screenshot", True):
        from sensehub.settings import get_settings
        settings = get_settings()
        path = settings.screenshots_dir / f"browser_{int(__import__('time').time())}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path))
        shot = str(path)
    return tool_result(True, data={
        "url": page.url,
        "title": page.title(),
        "refs": refs,
        "ref_count": len(refs),
        "screenshot_path": shot,
    })


def browser_act(params: dict[str, Any]) -> dict[str, Any]:
    action = str(params.get("action", "click")).lower()
    ref = str(params.get("ref", "")).strip()
    value = params.get("value", "")
    page = _active_page()
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
    return tool_result(True, data={"action": action, "ref": ref, "label": target.get("label"), "url": page.url})


def browser_click(params: dict[str, Any]) -> dict[str, Any]:
    selector = str(params.get("selector", "")).strip()
    if not selector:
        raise ValueError("selector 不能为空")
    timeout = int(params.get("timeout", 30000))
    page = _active_page()
    el = page.wait_for_selector(selector, timeout=timeout)
    if not el:
        raise RuntimeError(f"未找到元素: {selector}")
    el.click()
    return tool_result(True, f"已点击: {selector}", data={"selector": selector, "url": page.url})


def browser_fill(params: dict[str, Any]) -> dict[str, Any]:
    selector = str(params.get("selector", "")).strip()
    value = params.get("value", "")
    if not selector:
        raise ValueError("selector 不能为空")
    timeout = int(params.get("timeout", 30000))
    page = _active_page()
    el = page.wait_for_selector(selector, timeout=timeout)
    if not el:
        raise RuntimeError(f"未找到元素: {selector}")
    el.fill(str(value))
    return tool_result(True, f"已填写: {selector}", data={"selector": selector, "value": value})


def browser_get_text(params: dict[str, Any]) -> dict[str, Any]:
    selector = str(params.get("selector", "")).strip()
    if not selector:
        raise ValueError("selector 不能为空")
    timeout = int(params.get("timeout", 10000))
    page = _active_page()
    el = page.wait_for_selector(selector, timeout=timeout)
    if not el:
        raise RuntimeError(f"未找到元素: {selector}")
    text = el.inner_text()
    return tool_result(True, data={"selector": selector, "text": text, "length": len(text)})


def browser_get_html(params: dict[str, Any]) -> dict[str, Any]:
    selector = str(params.get("selector", "body")).strip()
    timeout = int(params.get("timeout", 10000))
    page = _active_page()
    if selector:
        el = page.wait_for_selector(selector, timeout=timeout)
        if not el:
            raise RuntimeError(f"未找到元素: {selector}")
        html = el.inner_html()
    else:
        html = page.content()
    return tool_result(True, data={"selector": selector or "full_page", "html": html, "length": len(html)})


def browser_wait(params: dict[str, Any]) -> dict[str, Any]:
    selector = str(params.get("selector", "")).strip()
    timeout = int(params.get("timeout", 30000))
    state = str(params.get("state", "visible"))
    page = _active_page()
    if not selector:
        page.wait_for_timeout(timeout)
        return tool_result(True, f"已等待 {timeout}ms", data={"waited_ms": timeout})
    el = page.wait_for_selector(selector, timeout=timeout, state=state)
    if not el:
        raise RuntimeError(f"等待超时，未出现: {selector}")
    return tool_result(True, f"元素已{state}: {selector}", data={"selector": selector, "state": state})


def browser_scroll(params: dict[str, Any]) -> dict[str, Any]:
    direction = str(params.get("direction", "down")).lower()
    amount = int(params.get("amount", 500))
    page = _active_page()
    if direction == "down":
        page.evaluate(f"window.scrollBy(0, {amount})")
    elif direction == "up":
        page.evaluate(f"window.scrollBy(0, -{amount})")
    elif direction == "bottom":
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    elif direction == "top":
        page.evaluate("window.scrollTo(0, 0)")
    return tool_result(True, f"已滚动 {direction} {amount}px", data={"direction": direction, "amount": amount})


# --- 标签页管理 ---

def browser_new_tab(params: dict[str, Any]) -> dict[str, Any]:
    url = str(params.get("url", "about:blank")).strip()
    page = _active_page().context.new_page()
    page.on("dialog", lambda dialog: dialog.accept())
    _pages.append(page)
    if url and url != "about:blank":
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        page.goto(url, wait_until="domcontentloaded")
    return tool_result(True, f"已新建标签页: {page.url}", data={"url": page.url, "tab_index": len(_pages) - 1})


def browser_switch_tab(params: dict[str, Any]) -> dict[str, Any]:
    global _pages
    index = params.get("index")
    title = str(params.get("title", "")).strip()
    url = str(params.get("url", "")).strip()

    if index is not None:
        idx = int(index)
        all_pages = [p for p in _pages if not p.is_closed()]
        if idx < 0 or idx >= len(all_pages):
            raise IndexError(f"标签页索引 {idx} 超出范围 (0-{len(all_pages) - 1})")
        target = all_pages[idx]
    elif title:
        target = _find_tab_by_title(title)
        if not target:
            raise RuntimeError(f"未找到标题包含 '{title}' 的标签页")
    elif url:
        target = _find_tab_by_url(url)
        if not target:
            raise RuntimeError(f"未找到 URL 包含 '{url}' 的标签页")
    else:
        raise ValueError("请指定 index、title 或 url 之一")

    target.bring_to_front()
    # 将激活的标签页移到列表末尾
    all_pages = [p for p in _pages if not p.is_closed()]
    if target in all_pages:
        all_pages.remove(target)
        all_pages.append(target)
    _pages = all_pages + [p for p in _pages if p.is_closed()]

    return tool_result(True, f"已切换到标签页: {target.title}", data={"url": target.url, "title": target.title})


def browser_close_tab(params: dict[str, Any]) -> dict[str, Any]:
    global _pages
    index = params.get("index")
    if index is None:
        index = -1  # 关闭当前标签页
    idx = int(index)
    all_pages = [p for p in _pages if not p.is_closed()]
    if idx < 0:
        idx = len(all_pages) + idx
    if idx < 0 or idx >= len(all_pages):
        raise IndexError(f"标签页索引 {idx} 超出范围")
    target = all_pages[idx]
    title = target.title
    target.close()
    _pages = [p for p in _pages if not p.is_closed() or p == target]
    return tool_result(True, f"已关闭标签页: {title}", data={"closed_title": title})


def browser_list_tabs(params: dict[str, Any]) -> dict[str, Any]:
    _ = params
    all_pages = [p for p in _pages if not p.is_closed()]
    tabs = []
    for i, p in enumerate(all_pages):
        tabs.append({
            "index": i,
            "title": p.title(),
            "url": p.url,
        })
    return tool_result(True, data={"tabs": tabs, "count": len(tabs)})


def _find_tab_by_title(title_substr: str):
    for p in _pages:
        if not p.is_closed() and title_substr.lower() in p.title().lower():
            return p
    return None


def _find_tab_by_url(url_substr: str):
    for p in _pages:
        if not p.is_closed() and url_substr.lower() in p.url.lower():
            return p
    return None


# --- 浏览器通用操作 ---

def browser_go_back(params: dict[str, Any]) -> dict[str, Any]:
    _ = params
    page = _active_page()
    page.go_back()
    return tool_result(True, f"已后退到: {page.url}", data={"url": page.url})


def browser_go_forward(params: dict[str, Any]) -> dict[str, Any]:
    _ = params
    page = _active_page()
    page.go_forward()
    return tool_result(True, f"已前进到: {page.url}", data={"url": page.url})


def browser_reload(params: dict[str, Any]) -> dict[str, Any]:
    _ = params
    page = _active_page()
    page.reload()
    return tool_result(True, f"已刷新: {page.url}", data={"url": page.url})


def browser_evaluate(params: dict[str, Any]) -> dict[str, Any]:
    script = str(params.get("script", "")).strip()
    if not script:
        raise ValueError("script 不能为空")
    page = _active_page()
    result = page.evaluate(script)
    return tool_result(True, data={"script": script, "result": str(result)[:2000]})


def browser_screenshot(params: dict[str, Any]) -> dict[str, Any]:
    from sensehub.settings import get_settings
    page = _active_page()
    settings = get_settings()
    path = settings.screenshots_dir / f"browser_{int(__import__('time').time())}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    selector = params.get("selector")
    if selector:
        el = page.wait_for_selector(str(selector), timeout=10000)
        if not el:
            raise RuntimeError(f"未找到元素: {selector}")
        el.screenshot(path=str(path))
    else:
        page.screenshot(path=str(path), full_page=bool(params.get("full_page", False)))
    return tool_result(True, f"浏览器截图已保存: {path}", data={"screenshot_path": str(path)})
