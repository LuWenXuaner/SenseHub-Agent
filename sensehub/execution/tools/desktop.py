"""桌面自动化."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

import pyautogui
import pyperclip

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.2

_NOTEPAD_TITLES = ("记事本", "Notepad", "无标题", "Untitled")

# 次级窗口（登录/扫码等）标题常见片段，聚焦时优先跳过
_LOGIN_TITLE_HINTS = ("登录", "login", "sign in", "扫码", "scan", "qrcode", "qr code", "授权")

APP_MAP = {
    "notepad": "notepad",
    "记事本": "notepad",
    "calc": "calc",
    "计算器": "calc",
    "chrome": "chrome",
    "浏览器": "chrome",
    "edge": "msedge",
    "msedge": "msedge",
    "explorer": "explorer",
    "资源管理器": "explorer",
    "文件管理器": "explorer",
}

_TITLE_ALIASES: dict[str, tuple[str, ...]] = {
    "notepad": _NOTEPAD_TITLES,
    "记事本": _NOTEPAD_TITLES,
    "calc": ("计算器", "Calculator"),
    "计算器": ("计算器", "Calculator"),
    "chrome": ("Chrome", "Google Chrome"),
    "浏览器": ("Chrome", "Edge", "Microsoft Edge", "Google Chrome"),
    "edge": ("Edge", "Microsoft Edge"),
    "msedge": ("Edge", "Microsoft Edge"),
    "explorer": ("文件资源管理器", "File Explorer"),
    "资源管理器": ("文件资源管理器", "File Explorer"),
    "wechat": ("微信", "WeChat"),
    "微信": ("微信", "WeChat"),
}

_START_MENU_ROOTS = (
    lambda: Path(os.environ.get("ProgramData", r"C:\ProgramData"))
    / "Microsoft/Windows/Start Menu/Programs",
    lambda: Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
    lambda: Path(os.environ.get("USERPROFILE", "")) / "Desktop",
)

_EXE_SEARCH_ROOTS = (
    lambda: Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
    lambda: Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
    lambda: Path(os.environ.get("LOCALAPPDATA", "")),
    lambda: Path(os.environ.get("APPDATA", "")),
)


def _title_keywords(name: str) -> tuple[str, ...]:
    key = name.strip().lower()
    if key in _TITLE_ALIASES:
        return _TITLE_ALIASES[key]
    if name.strip() in _TITLE_ALIASES:
        return _TITLE_ALIASES[name.strip()]
    stripped = name.strip()
    return (stripped,) if stripped else _NOTEPAD_TITLES


def _name_match(query: str, candidate: str) -> bool:
    q = query.strip().lower()
    c = candidate.strip().lower()
    if not q or not c:
        return False
    return q == c or q in c or c in q


def _find_start_menu_shortcut(query: str) -> Path | None:
    """在开始菜单/桌面快捷方式中按显示名匹配（通用，非个案表）."""
    exact: Path | None = None
    partial: Path | None = None
    for root_fn in _START_MENU_ROOTS:
        root = root_fn()
        if not root.is_dir():
            continue
        try:
            entries = list(root.rglob("*.lnk"))
        except OSError:
            continue
        for path in entries[:800]:
            stem = path.stem
            if stem.lower() == query.strip().lower():
                return path
            if _name_match(query, stem):
                partial = partial or path
    return exact or partial


def _find_installed_exe(query: str) -> Path | None:
    """在常见安装目录搜索与名称匹配的 exe（stem 互相包含）."""
    q = query.strip().lower()
    if not q:
        return None
    best: Path | None = None
    best_score = -1
    for root_fn in _EXE_SEARCH_ROOTS:
        root = root_fn()
        if not root.is_dir():
            continue
        try:
            for exe in root.rglob("*.exe"):
                if exe.stat().st_size <= 0:
                    continue
                stem = exe.stem.lower()
                if stem == q:
                    return exe
                if _name_match(q, stem):
                    score = len(stem)
                    if score > best_score:
                        best = exe
                        best_score = score
        except OSError:
            continue
    return best


def _window_area(hwnd: int) -> int:
    import win32gui

    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        return max(0, right - left) * max(0, bottom - top)
    except Exception:
        return 0


def _get_process_image_name(pid: int) -> str:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buf))
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return Path(buf.value).name.lower()
    finally:
        kernel32.CloseHandle(handle)
    return ""


def _find_windows_by_processes(image_names: tuple[str, ...]) -> list[tuple[int, str, int]]:
    import win32gui
    import win32process

    targets = {name.lower() for name in image_names if name}
    if not targets:
        return []

    matches: list[tuple[int, str, int]] = []

    def _enum(hwnd: int, _: object) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        image = _get_process_image_name(pid)
        if image in targets:
            matches.append((hwnd, title, _window_area(hwnd)))

    win32gui.EnumWindows(_enum, None)
    return matches


def _launch_target(raw_name: str) -> tuple[list[str], tuple[str, ...], tuple[str, ...]]:
    """解析启动目标：内置命令 → 开始菜单快捷方式 → 已安装 exe."""
    process_images: tuple[str, ...] = ()
    name_key = raw_name.strip().lower()
    if name_key in APP_MAP:
        exe = APP_MAP[name_key]
        return ["cmd", "/c", "start", "", exe], _title_keywords(name_key), process_images
    if raw_name.strip() in APP_MAP:
        exe = APP_MAP[raw_name.strip()]
        return ["cmd", "/c", "start", "", exe], _title_keywords(raw_name.strip()), process_images

    shortcut = _find_start_menu_shortcut(raw_name)
    if shortcut:
        keywords = (raw_name.strip(), shortcut.stem)
        for candidate in (raw_name, shortcut.stem, *_TITLE_ALIASES.get(raw_name.strip(), ()), *_TITLE_ALIASES.get(name_key, ())):
            exe_path = _find_installed_exe(str(candidate))
            if exe_path:
                process_images = (exe_path.name,)
                break
        return ["cmd", "/c", "start", "", str(shortcut)], keywords, process_images

    exe_path = _find_installed_exe(raw_name)
    if exe_path:
        keywords = (raw_name.strip(), exe_path.stem)
        process_images = (exe_path.name,)
        return ["cmd", "/c", "start", "", str(exe_path)], keywords, process_images

    raise ValueError(
        f"未找到应用「{raw_name}」。请确认已安装，或尝试开始菜单中的准确名称。"
    )


def _is_loginish_title(title: str) -> bool:
    lowered = title.lower()
    return any(hint.lower() in lowered for hint in _LOGIN_TITLE_HINTS)


def _find_matching_windows(title_keywords: tuple[str, ...]) -> list[tuple[int, str, int]]:
    import win32gui

    matches: list[tuple[int, str, int]] = []

    def _enum(hwnd: int, _: object) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return
        if any(k.lower() in title.lower() for k in title_keywords):
            matches.append((hwnd, title, _window_area(hwnd)))

    win32gui.EnumWindows(_enum, None)
    return matches


def _pick_best_window(matches: list[tuple[int, str, int]]) -> tuple[int, str] | None:
    if not matches:
        return None
    non_login = [m for m in matches if not _is_loginish_title(m[1])]
    pool = non_login if non_login else matches
    pool.sort(key=lambda item: item[2], reverse=True)
    hwnd, title, _ = pool[0]
    return hwnd, title


def _focus_hwnd(hwnd: int) -> bool:
    import win32con
    import win32gui
    import win32process

    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        fg = win32gui.GetForegroundWindow()
        fg_tid = win32process.GetWindowThreadProcessId(fg)[0]
        tgt_tid = win32process.GetWindowThreadProcessId(hwnd)[0]
        if fg_tid != tgt_tid:
            win32process.AttachThreadInput(fg_tid, tgt_tid, True)
        win32gui.SetForegroundWindow(hwnd)
        if fg_tid != tgt_tid:
            win32process.AttachThreadInput(fg_tid, tgt_tid, False)
        time.sleep(0.4)
        return True
    except Exception:
        return False


def _focus_window(title_keywords: tuple[str, ...], timeout: float = 6.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        matches = _find_matching_windows(title_keywords)
        best = _pick_best_window(matches)
        if best and _focus_hwnd(best[0]):
            return True
        time.sleep(0.25)
    return False


def _find_window_hwnd(title_keywords: tuple[str, ...], timeout: float = 5.0) -> int | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        best = _pick_best_window(_find_matching_windows(title_keywords))
        if best:
            return best[0]
        time.sleep(0.25)
    return None


def _paste_text(text: str) -> None:
    pyperclip.copy(text)
    time.sleep(0.05)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.15)


def window_matches_app(foreground_title: str, app_name: str) -> bool:
    """前台窗口标题是否属于目标应用（含主窗口标题为联系人名等情况）."""
    if not foreground_title or not app_name:
        return True
    if any(k.lower() in foreground_title.lower() for k in _title_keywords(app_name)):
        return True
    try:
        _, _, process_images = _launch_target(app_name)
    except ValueError:
        return False
    if not process_images:
        return False
    for _, title, _ in _find_windows_by_processes(process_images):
        if title == foreground_title:
            return True
    return False


def _existing_app_windows(
    keywords: tuple[str, ...],
    process_images: tuple[str, ...],
) -> list[tuple[int, str, int]]:
    by_title = _find_matching_windows(keywords)
    if by_title:
        return by_title
    return _find_windows_by_processes(process_images)


def open_app(params: dict[str, Any]) -> dict[str, Any]:
    raw_name = str(params.get("name", "")).strip()
    if not raw_name:
        raise ValueError("未指定应用名称")

    argv, keywords, process_images = _launch_target(raw_name)
    reuse_if_open = params.get("reuse_if_open", True)
    existing = _existing_app_windows(keywords, process_images)

    if existing and reuse_if_open:
        best = _pick_best_window(existing)
        focused_window = best[1] if best else existing[0][1]
        focused = bool(best and _focus_hwnd(best[0]))
        titles = [title for _, title, _ in existing]
        return {
            "opened": raw_name,
            "launched": False,
            "already_running": True,
            "matching_windows": titles,
            "window_count": len(existing),
            "focused_window": focused_window,
            "focused": focused,
        }

    subprocess.Popen(argv, shell=False)

    focused = False
    focused_window = ""
    if params.get("focus", True):
        time.sleep(0.8)
        focused = _focus_window(keywords)
        if not focused and process_images:
            proc_matches = _find_windows_by_processes(process_images)
            best = _pick_best_window(proc_matches)
            if best:
                focused = _focus_hwnd(best[0])
                if focused:
                    focused_window = best[1]
        elif focused:
            best = _pick_best_window(_existing_app_windows(keywords, process_images))
            if best:
                focused_window = best[1]

    after = _existing_app_windows(keywords, process_images)
    titles = [title for _, title, _ in after]
    return {
        "opened": raw_name,
        "launch": argv[-1],
        "launched": True,
        "already_running": False,
        "matching_windows": titles,
        "window_count": len(after),
        "focused_window": focused_window,
        "focused": focused,
    }


def focus_window(params: dict[str, Any]) -> dict[str, Any]:
    title = str(params.get("title") or params.get("name") or "").strip()
    if not title:
        raise ValueError("未指定窗口 title/name")
    keywords = _title_keywords(title)
    if not _focus_window(keywords, timeout=float(params.get("timeout", 6))):
        raise RuntimeError(f"未找到窗口: {title}")
    return {"focused": title, "keywords": list(keywords)}


def close_app(params: dict[str, Any]) -> dict[str, Any]:
    title = str(params.get("title") or params.get("name") or "").strip()
    if not title:
        raise ValueError("未指定要关闭的应用 title/name")
    keywords = _title_keywords(title)
    if not _focus_window(keywords, timeout=float(params.get("timeout", 5))):
        raise RuntimeError(f"未找到窗口: {title}")
    method = str(params.get("method", "alt_f4")).lower()
    if method == "hotkey" and params.get("keys"):
        keys = params["keys"]
        if isinstance(keys, str):
            keys = [k.strip() for k in keys.replace("+", " ").split() if k.strip()]
        pyautogui.hotkey(*keys)
    else:
        pyautogui.hotkey("alt", "f4")
    time.sleep(0.35)
    return {"closed": title, "method": method}


def list_windows(params: dict[str, Any]) -> dict[str, Any]:
    import win32gui

    limit = int(params.get("limit", 40))
    titles: list[str] = []

    def _enum(hwnd: int, _: object) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        t = win32gui.GetWindowText(hwnd).strip()
        if t:
            titles.append(t)

    win32gui.EnumWindows(_enum, None)
    return {"windows": titles[:limit], "count": len(titles)}


def active_window(params: dict[str, Any]) -> dict[str, Any]:
    """返回当前前台窗口（操作前确认焦点）."""
    import win32gui

    _ = params
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd).strip()
    return {"title": title or "(无标题)", "hwnd": int(hwnd)}


def minimize_window(params: dict[str, Any]) -> dict[str, Any]:
    import win32con
    import win32gui

    title = str(params.get("title") or params.get("name") or "").strip()
    hwnd = _find_window_hwnd(_title_keywords(title))
    if not hwnd:
        raise RuntimeError(f"未找到窗口: {title}")
    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    return {"minimized": title}


def maximize_window(params: dict[str, Any]) -> dict[str, Any]:
    import win32con
    import win32gui

    title = str(params.get("title") or params.get("name") or "").strip()
    hwnd = _find_window_hwnd(_title_keywords(title))
    if not hwnd:
        raise RuntimeError(f"未找到窗口: {title}")
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    return {"maximized": title}


def press_key(params: dict[str, Any]) -> dict[str, Any]:
    keys = params.get("keys") or params.get("key")
    if isinstance(keys, str):
        if "+" in keys or " " in keys:
            parts = [k.strip() for k in keys.replace("+", " ").split() if k.strip()]
            pyautogui.hotkey(*parts)
            return {"keys": parts}
        pyautogui.press(keys)
        return {"key": keys}
    if isinstance(keys, list) and keys:
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
        return {"keys": keys}
    raise ValueError("keys 不能为空")


def type_text(params: dict[str, Any]) -> dict[str, Any]:
    text = params.get("text", "")
    if not text:
        raise ValueError("text 不能为空")

    import win32gui

    foreground = win32gui.GetWindowText(win32gui.GetForegroundWindow()).strip()

    app = params.get("app", "").strip().lower()
    if app in ("notepad", "记事本"):
        if not _focus_window(_NOTEPAD_TITLES, timeout=4.0):
            raise RuntimeError("未找到记事本窗口，请先打开记事本")
    elif app:
        keywords = _title_keywords(app)
        if not _focus_window(keywords, timeout=4.0):
            _, _, process_images = _launch_target(app)
            proc_matches = _find_windows_by_processes(process_images)
            best = _pick_best_window(proc_matches)
            if not best or not _focus_hwnd(best[0]):
                raise RuntimeError(f"未找到窗口: {app}")

    time.sleep(0.2)
    foreground_after = win32gui.GetWindowText(win32gui.GetForegroundWindow()).strip()

    # pyautogui.write 仅支持 ASCII；中文等用剪贴板粘贴
    if any(ord(ch) > 127 for ch in text):
        _paste_text(text)
        method = "paste"
    else:
        pyautogui.write(text, interval=0.02)
        method = "write"

    return {
        "typed_length": len(text),
        "method": method,
        "text": text,
        "foreground_window": foreground_after or foreground,
        "app_requested": app or None,
    }
