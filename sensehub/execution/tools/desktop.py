"""桌面自动化."""

from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import pyautogui
import pyperclip

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

_VK = {
    "ctrl": 0x11,
    "control": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "f4": 0x73,
    "esc": 0x1B,
    "escape": 0x1B,
}


def _hotkey_vks(*vk_codes: int) -> None:
    """Win32 keybd_event 组合键，比 pyautogui 更可靠地发到前台窗口."""
    import win32api
    import win32con

    for vk in vk_codes:
        win32api.keybd_event(vk, 0, 0, 0)
    for vk in reversed(vk_codes):
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(0.04)


def _hotkey_chord(*vk_codes: int) -> None:
    """按住修饰键再按主键，间隔更接近真人操作."""
    import win32api
    import win32con

    for vk in vk_codes:
        win32api.keybd_event(vk, 0, 0, 0)
        time.sleep(0.02)
    time.sleep(0.03)
    for vk in reversed(vk_codes):
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.02)
    time.sleep(0.05)


def _hotkey_names(*names: str) -> None:
    vks: list[int] = []
    for name in names:
        key = str(name).strip().lower()
        if key in _VK:
            vks.append(_VK[key])
        elif len(key) == 1:
            vks.append(ord(key.upper()))
        else:
            raise ValueError(f"不支持的按键: {name}")
    _hotkey_vks(*vks)


def _press_vk(vk: int) -> None:
    import win32api
    import win32con

    win32api.keybd_event(vk, 0, 0, 0)
    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(0.04)

_NOTEPAD_TITLES = ("记事本", "Notepad", "无标题", "Untitled")

# 次级窗口（登录/扫码等）标题常见片段，聚焦时优先跳过（避免过宽词如「授权」误伤主窗口）
_LOGIN_TITLE_HINTS = (
    "登录",
    "login",
    "sign in",
    "sign-in",
    "扫码",
    "scan qr",
    "qrcode",
    "qr code",
    "请登录",
    "账号登录",
    "微信登录",
    "qq登录",
)

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

# 内置应用对应进程名（标题为联系人名等时仍能识别已打开实例）
APP_PROCESS_IMAGES: dict[str, tuple[str, ...]] = {
    "notepad": ("notepad.exe",),
    "记事本": ("notepad.exe",),
    "calc": ("calculatorapp.exe", "calculator.exe", "win32calc.exe"),
    "计算器": ("calculatorapp.exe", "calculator.exe", "win32calc.exe"),
    "chrome": ("chrome.exe",),
    "浏览器": ("chrome.exe", "msedge.exe"),
    "edge": ("msedge.exe",),
    "msedge": ("msedge.exe",),
    "explorer": ("explorer.exe",),
    "资源管理器": ("explorer.exe",),
    "文件管理器": ("explorer.exe",),
    "wechat": ("weixin.exe", "wechat.exe"),
    "微信": ("weixin.exe", "wechat.exe"),
    "钉钉": ("dingtalk.exe",),
    "dingtalk": ("dingtalk.exe",),
    "飞书": ("feishu.exe",),
    "feishu": ("feishu.exe",),
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


def _clamp_wait(value: Any, *, default: float, min_v: float = 0.0, max_v: float = 20.0) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    return max(min_v, min(max_v, num))


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


def _pids_for_process_images(image_names: tuple[str, ...]) -> set[int]:
    """进程快照查 PID，避免 EnumWindows 时对每个窗口 OpenProcess."""
    targets = {name.lower() for name in image_names if name}
    if not targets:
        return set()

    import ctypes
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot in (-1, 0xFFFFFFFF):
        return set()

    pids: set[int] = set()
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            while True:
                if entry.szExeFile.lower() in targets:
                    pids.add(int(entry.th32ProcessID))
                if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)
    return pids


def _find_windows_by_processes(image_names: tuple[str, ...]) -> list[tuple[int, str, int]]:
    import win32gui
    import win32process

    target_pids = _pids_for_process_images(image_names)
    if not target_pids:
        return []

    matches: list[tuple[int, str, int]] = []

    def _enum(hwnd: int, _: object) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid in target_pids:
            matches.append((hwnd, title, _window_area(hwnd)))

    win32gui.EnumWindows(_enum, None)
    return matches


def _process_images_for_known_app(raw_name: str) -> tuple[str, ...]:
    """已知应用直接返回进程名，避免全盘搜索 exe."""
    key = raw_name.strip().lower()
    if key in APP_PROCESS_IMAGES:
        return APP_PROCESS_IMAGES[key]
    raw = raw_name.strip()
    if raw in APP_PROCESS_IMAGES:
        return APP_PROCESS_IMAGES[raw]
    return ()


def _launch_target(raw_name: str) -> tuple[list[str], tuple[str, ...], tuple[str, ...]]:
    """解析启动目标：内置命令 → 开始菜单快捷方式 → 已安装 exe."""
    name_key = raw_name.strip().lower()
    if name_key in APP_MAP:
        exe = APP_MAP[name_key]
        proc = _process_images_for(name_key, raw_name, exe)
        return ["cmd", "/c", "start", "", exe], _title_keywords(name_key), proc
    if raw_name.strip() in APP_MAP:
        exe = APP_MAP[raw_name.strip()]
        proc = _process_images_for(name_key, raw_name, exe)
        return ["cmd", "/c", "start", "", exe], _title_keywords(raw_name.strip()), proc

    keywords = _title_keywords(raw_name)
    known_proc = _process_images_for_known_app(raw_name)
    if known_proc:
        shortcut = _find_start_menu_shortcut(raw_name)
        if shortcut:
            return ["cmd", "/c", "start", "", str(shortcut)], keywords, known_proc
        return ["cmd", "/c", "start", "", raw_name.strip()], keywords, known_proc

    process_images: tuple[str, ...] = ()
    shortcut = _find_start_menu_shortcut(raw_name)
    if shortcut:
        keywords = (raw_name.strip(), shortcut.stem)
        alias_images: list[str] = []
        for candidate in (
            raw_name,
            shortcut.stem,
            *_TITLE_ALIASES.get(raw_name.strip(), ()),
            *_TITLE_ALIASES.get(name_key, ()),
        ):
            for img in APP_PROCESS_IMAGES.get(str(candidate).strip().lower(), ()):
                if img not in alias_images:
                    alias_images.append(img)
            if not alias_images:
                exe_path = _find_installed_exe(str(candidate))
                if exe_path and exe_path.name not in alias_images:
                    alias_images.append(exe_path.name)
        process_images = tuple(alias_images) if alias_images else process_images
        if not process_images:
            exe_path = _find_installed_exe(raw_name)
            if exe_path:
                process_images = (exe_path.name,)
        return ["cmd", "/c", "start", "", str(shortcut)], keywords, process_images

    exe_path = _find_installed_exe(raw_name)
    if exe_path:
        keywords = (raw_name.strip(), exe_path.stem)
        extra = APP_PROCESS_IMAGES.get(name_key, ())
        process_images = (exe_path.name, *extra) if extra else (exe_path.name,)
        return ["cmd", "/c", "start", "", str(exe_path)], keywords, process_images

    raise ValueError(
        f"未找到应用「{raw_name}」。请确认已安装，或尝试开始菜单中的准确名称。"
    )


def _is_loginish_title(title: str) -> bool:
    lowered = title.lower()
    return any(hint.lower() in lowered for hint in _LOGIN_TITLE_HINTS)


def is_login_title(title: str) -> bool:
    """窗口标题是否像登录/扫码界面（供 Harness 门禁）."""
    return _is_loginish_title(title)


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


def _pick_best_window(matches: list[tuple[int, str, int]], *, app: str | None = None) -> tuple[int, str] | None:
    if not matches:
        return None
    non_login = [m for m in matches if not _is_loginish_title(m[1])]
    pool = non_login if non_login else matches
    pool.sort(key=lambda item: item[2], reverse=True)
    hwnd, title, _ = pool[0]
    return hwnd, title


def _foreground_matches_hwnd(hwnd: int) -> bool:
    import win32gui
    import win32process

    try:
        fg = win32gui.GetForegroundWindow()
        if not fg:
            return False
        if fg == hwnd:
            return True
        try:
            ga_root = 2  # GA_ROOT
            if win32gui.GetAncestor(fg, ga_root) == hwnd:
                return True
            if win32gui.GetAncestor(hwnd, ga_root) == fg:
                return True
        except Exception:
            pass
        _, fg_pid = win32process.GetWindowThreadProcessId(fg)
        _, tgt_pid = win32process.GetWindowThreadProcessId(hwnd)
        return fg_pid == tgt_pid and tgt_pid != 0
    except Exception:
        return False


def _measure_focus_for_app(
    raw_name: str,
    keywords: tuple[str, ...],
    process_images: tuple[str, ...],
) -> dict[str, Any]:
    """综合判断目标应用是否已在前台（比单次 SetForegroundWindow 返回值更贴近肉眼所见）."""
    import win32gui

    fg = win32gui.GetForegroundWindow()
    fg_title = win32gui.GetWindowText(fg).strip() if fg else ""
    best = _pick_best_window(_existing_app_windows(keywords, process_images))
    target_hwnd = best[0] if best else None
    target_title = best[1] if best else ""

    hwnd_match = bool(target_hwnd and _foreground_matches_hwnd(target_hwnd))
    title_match = window_matches_app(fg_title, raw_name)
    visible_ready = False
    if target_hwnd:
        try:
            visible_ready = bool(
                win32gui.IsWindowVisible(target_hwnd)
                and not win32gui.IsIconic(target_hwnd)
            )
        except Exception:
            visible_ready = False

    # 窗口已可见且前台标题/进程/HWND 任一匹配 → 视为置前成功
    focus_verified = hwnd_match or title_match
    if not focus_verified and visible_ready and target_hwnd and fg:
        try:
            import win32process

            _, fg_pid = win32process.GetWindowThreadProcessId(fg)
            _, tgt_pid = win32process.GetWindowThreadProcessId(target_hwnd)
            if fg_pid == tgt_pid and tgt_pid != 0:
                focus_verified = True
        except Exception:
            pass

    return {
        "foreground_window": fg_title or "(无标题)",
        "foreground_matches": title_match or hwnd_match,
        "focus_verified": focus_verified,
        "target_window": target_title,
        "target_visible": visible_ready,
    }


def _finalize_open_focus(
    raw_name: str,
    keywords: tuple[str, ...],
    process_images: tuple[str, ...],
    *,
    focus_attempted: bool,
    focus_api_ok: bool,
) -> dict[str, Any]:
    measured = _measure_focus_for_app(raw_name, keywords, process_images)
    target_title = str(measured["target_window"] or "")
    target_matches = bool(target_title) and window_matches_app(target_title, raw_name)
    # 小窗置前即可；Hub 浏览器抢回前台不影响（type_text 会再次聚焦后粘贴）
    verified = (
        focus_api_ok
        or bool(measured["focus_verified"])
        or (bool(measured["target_visible"]) and target_matches)
    )
    return {
        "focused": verified,
        "focus_api_ok": focus_api_ok,
        "focus_verified": verified,
        "foreground_window": measured["foreground_window"],
        "foreground_matches": measured["foreground_matches"],
        "focused_window": target_title or measured["foreground_window"],
        "target_visible": measured["target_visible"],
        "focus_attempted": focus_attempted,
    }


def _is_notepad_app(app: str) -> bool:
    k = app.strip().lower()
    return k in ("notepad", "记事本")


def _is_im_app(app: str) -> bool:
    k = app.strip().lower()
    return k in ("wechat", "微信", "钉钉", "dingtalk", "飞书", "feishu")


def _allow_set_foreground() -> None:
    try:
        import ctypes

        ctypes.windll.user32.AllowSetForegroundWindow(ctypes.c_uint32(0xFFFFFFFF))
    except Exception:
        pass


def _focus_hwnd(
    hwnd: int,
    *,
    click_center: bool = False,
    app_for_click: str | None = None,
    post_focus_wait: float = 0.35,
    aggressive: bool = True,
) -> bool:
    import win32con
    import win32gui
    import win32process

    try:
        _allow_set_foreground()
        attempts = 3 if aggressive else 1
        for _ in range(attempts):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            if aggressive:
                win32gui.BringWindowToTop(hwnd)
                try:
                    # TOPMOST/NOTOPMOST 能显著提高部分应用被置前成功率（仅首次打开时用）
                    win32gui.SetWindowPos(
                        hwnd,
                        win32con.HWND_TOPMOST,
                        0,
                        0,
                        0,
                        0,
                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                    )
                    win32gui.SetWindowPos(
                        hwnd,
                        win32con.HWND_NOTOPMOST,
                        0,
                        0,
                        0,
                        0,
                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                    )
                except Exception:
                    pass

            fg = win32gui.GetForegroundWindow()
            fg_tid = win32process.GetWindowThreadProcessId(fg)[0]
            tgt_tid = win32process.GetWindowThreadProcessId(hwnd)[0]
            attached = False
            if fg_tid != tgt_tid:
                win32process.AttachThreadInput(fg_tid, tgt_tid, True)
                attached = True
            win32gui.SetForegroundWindow(hwnd)
            if attached:
                win32process.AttachThreadInput(fg_tid, tgt_tid, False)

            time.sleep(post_focus_wait)
            if _foreground_matches_hwnd(hwnd):
                break

        if not _foreground_matches_hwnd(hwnd):
            return False
        if click_center:
            _click_edit_area(hwnd, app_for_click)
        return True
    except Exception:
        return False


def _focus_window(
    title_keywords: tuple[str, ...],
    process_images: tuple[str, ...] = (),
    *,
    timeout: float = 6.0,
    click_center: bool = False,
    app_for_click: str | None = None,
    post_focus_wait: float = 0.35,
    aggressive: bool = True,
) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        matches = _existing_app_windows(title_keywords, process_images)
        best = _pick_best_window(matches)
        if best and _focus_hwnd(
            best[0],
            click_center=click_center,
            app_for_click=app_for_click,
            post_focus_wait=post_focus_wait,
            aggressive=aggressive,
        ):
            return True
        time.sleep(0.25)
    return False


def _find_window_hwnd(
    title_keywords: tuple[str, ...],
    process_images: tuple[str, ...] = (),
    timeout: float = 5.0,
) -> int | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        best = _pick_best_window(_existing_app_windows(title_keywords, process_images))
        if best:
            return best[0]
        time.sleep(0.25)
    return None


def window_matches_app(foreground_title: str, app_name: str) -> bool:
    """前台窗口标题是否属于目标应用（含主窗口标题为联系人名等情况）."""
    if not foreground_title or not app_name:
        return True
    if any(k.lower() in foreground_title.lower() for k in _title_keywords(app_name)):
        return True
    _, process_images = _resolve_app_target(app_name)
    if not process_images:
        return False
    fg = foreground_title.strip()
    for _, title, _ in _find_windows_by_processes(process_images):
        if title == fg:
            return True
    # 前台标题可能是联系人名，只要同进程有可见主窗且已聚焦到该进程即可
    import win32gui
    import win32process

    hwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    image = _get_process_image_name(pid)
    return image in {n.lower() for n in process_images}


def _nudge_app_focus(app: str) -> None:
    """置前目标应用一次，便于紧接着发 Ctrl+V / Ctrl+S；记事本会点击编辑区."""
    if not app.strip():
        return
    if _is_notepad_app(app):
        ensure_app_focus_for_input(app, click_edit=True, aggressive=True, post_wait=0.18)
        return
    keywords, process_images = _resolve_app_target(app)
    _focus_window(
        keywords,
        process_images,
        timeout=3.0,
        click_center=False,
        app_for_click=app,
        post_focus_wait=0.12,
        aggressive=True,
    )


def _resolve_notepad_save_path(params: dict[str, Any]) -> Path:
    from sensehub.security.sandbox import default_save_dir

    raw_name = str(params.get("filename") or params.get("path") or "note.txt").strip()
    if not raw_name:
        raw_name = "note.txt"
    target = Path(raw_name)
    if not target.is_absolute():
        target = (default_save_dir() / target.name).resolve()
    else:
        target = target.expanduser().resolve()
    if target.suffix.lower() != ".txt":
        target = target.with_suffix(".txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _wait_notepad_file_hwnd(path: Path, *, timeout: float = 8.0) -> int | None:
    """等待记事本打开指定文件后的窗口句柄（不强抢焦点）."""
    import win32gui

    name = path.name
    stem = path.stem
    deadline = time.time() + timeout
    keywords, process_images = _resolve_app_target("notepad")
    while time.time() < deadline:
        for hwnd, title, _pid in _existing_app_windows(keywords, process_images):
            low = title.lower()
            if name.lower() in low or stem.lower() in low:
                if win32gui.IsWindowVisible(hwnd):
                    return hwnd
        time.sleep(0.2)
    return _find_window_hwnd(keywords, process_images, timeout=0.5)


def _close_hwnd_quiet(hwnd: int) -> bool:
    """优先 WM_CLOSE 关窗，避免 Alt+Tab 切屏."""
    import win32con
    import win32gui

    if not hwnd or not win32gui.IsWindow(hwnd):
        return True
    title = win32gui.GetWindowText(hwnd).strip()
    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        time.sleep(0.45)
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            return True
    except Exception:
        pass
    if _focus_hwnd(hwnd, aggressive=False, post_focus_wait=0.12):
        _hotkey_names("alt", "f4")
        time.sleep(0.4)
    gone = not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd)
    return gone


def _open_notepad_with_file(path: Path) -> dict[str, Any]:
    """用记事本打开已有文件；内容已在磁盘，不抢焦点、不粘贴."""
    subprocess.Popen(["notepad.exe", str(path)], shell=False)
    hwnd = _wait_notepad_file_hwnd(path, timeout=8.0)
    if not hwnd:
        raise RuntimeError("记事本已启动但未检测到文件窗口")
    import win32gui

    title = win32gui.GetWindowText(hwnd).strip()
    return {"opened": "notepad", "focused_window": title, "file_path": str(path), "hwnd": hwnd}


def _paste_text(text: str) -> None:
    """剪贴板 + Ctrl+V 粘贴到当前焦点."""
    pyperclip.copy(text)
    time.sleep(0.12)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.15)


def _process_images_for(name_key: str, raw_name: str, exe: str) -> tuple[str, ...]:
    if name_key in APP_PROCESS_IMAGES:
        return APP_PROCESS_IMAGES[name_key]
    if raw_name.strip() in APP_PROCESS_IMAGES:
        return APP_PROCESS_IMAGES[raw_name.strip()]
    if exe and not exe.endswith(".exe"):
        return (f"{exe}.exe",)
    return (exe,) if exe else ()


def _merge_window_matches(*groups: list[tuple[int, str, int]]) -> list[tuple[int, str, int]]:
    merged: dict[int, tuple[int, str, int]] = {}
    for group in groups:
        for item in group:
            merged[item[0]] = item
    return list(merged.values())


_IM_MIN_WINDOW_AREA = 280 * 200  # 过滤 IM 托盘提示等小窗，避免误聚焦


def _existing_app_windows(
    keywords: tuple[str, ...],
    process_images: tuple[str, ...],
) -> list[tuple[int, str, int]]:
    by_title = _find_matching_windows(keywords)
    by_proc = _find_windows_by_processes(process_images) if process_images else []
    if by_title and by_proc:
        merged = _merge_window_matches(by_title, by_proc)
    elif by_title:
        merged = by_title
    elif by_proc:
        merged = by_proc
    else:
        return []
    sized = [m for m in merged if m[2] >= _IM_MIN_WINDOW_AREA]
    return sized if sized else merged


def _login_screen_detected(
    titles: list[str],
    keywords: tuple[str, ...],
    process_images: tuple[str, ...],
    focused_window: str,
) -> bool:
    """仅当确认只有登录/扫码窗、且不存在已登录主窗口时为真."""
    all_windows = _existing_app_windows(keywords, process_images)
    if not all_windows:
        return bool(focused_window and _is_loginish_title(focused_window))
    non_login = [t for _, t, _ in all_windows if not _is_loginish_title(t)]
    if non_login:
        return False
    return any(_is_loginish_title(t) for t in titles) or (
        bool(focused_window) and _is_loginish_title(focused_window)
    )


def _click_client_point(hwnd: int, rel_x: float, rel_y: float) -> None:
    """在客户区相对坐标点击（0–1），用于把键盘焦点落到编辑区."""
    import win32gui

    try:
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        width = max(0, right - left)
        height = max(0, bottom - top)
        if width < 4 or height < 4:
            return
        cx = max(8, int(width * max(0.08, min(0.92, rel_x))))
        cy = max(8, int(height * max(0.08, min(0.92, rel_y))))
        sx, sy = win32gui.ClientToScreen(hwnd, (cx, cy))
        pyautogui.click(sx, sy)
        time.sleep(0.15)
    except Exception:
        pass


def _edit_area_position(app: str | None) -> tuple[float, float]:
    if app and _is_notepad_app(app):
        return 0.5, 0.72
    if app and _is_im_app(app):
        return 0.5, 0.88
    return 0.5, 0.5


def _click_edit_area(hwnd: int, app: str | None = None) -> None:
    rx, ry = _edit_area_position(app)
    _click_client_point(hwnd, rx, ry)


def _click_client_center(hwnd: int) -> None:
    _click_edit_area(hwnd, None)


def _resolve_app_target(app: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if _is_notepad_app(app):
        return _NOTEPAD_TITLES, ("notepad.exe",)
    name_key = app.strip().lower()
    keywords = _title_keywords(app)
    # 已知 IM/桌面应用：直接用进程名，避免 _launch_target 全盘 rglob *.exe（可达数十秒）
    if name_key in APP_PROCESS_IMAGES:
        return keywords, APP_PROCESS_IMAGES[name_key]
    raw = app.strip()
    if raw in APP_PROCESS_IMAGES:
        return keywords, APP_PROCESS_IMAGES[raw]
    try:
        _, _, process_images = _launch_target(app)
    except ValueError:
        process_images = ()
    return keywords, process_images


def foreground_is_app(app: str) -> bool:
    """前台是否已是目标应用（标题或进程/HWND）."""
    import win32gui

    if not app.strip():
        return False
    fg_title = win32gui.GetWindowText(win32gui.GetForegroundWindow()).strip()
    if window_matches_app(fg_title, app):
        return True
    keywords, process_images = _resolve_app_target(app)
    best = _pick_best_window(_existing_app_windows(keywords, process_images))
    return bool(best and _foreground_matches_hwnd(best[0]))


def ensure_app_focus_for_input(
    app: str,
    *,
    click_edit: bool | None = None,
    aggressive: bool = False,
    timeout: float = 5.0,
    post_wait: float = 0.2,
) -> tuple[bool, str, int | None]:
    """确保目标应用在前台且编辑区可输入；已聚焦时避免 TOPMOST 抢焦点."""
    import win32gui

    if not app.strip():
        return False, "", None
    if click_edit is None:
        click_edit = _is_notepad_app(app) or _is_im_app(app)

    keywords, process_images = _resolve_app_target(app)
    best = _pick_best_window(_existing_app_windows(keywords, process_images))
    if not best:
        return False, "", None
    hwnd, title = best

    fg_title = win32gui.GetWindowText(win32gui.GetForegroundWindow()).strip()
    already_focused = foreground_is_app(app)

    if already_focused and not aggressive:
        return True, fg_title or title, hwnd

    focused = _focus_window(
        keywords,
        process_images,
        timeout=timeout,
        click_center=click_edit,
        app_for_click=app,
        post_focus_wait=post_wait,
        aggressive=aggressive or not already_focused,
    )
    if not focused and not aggressive:
        focused = _focus_window(
            keywords,
            process_images,
            timeout=max(2.0, timeout * 0.6),
            click_center=click_edit,
            app_for_click=app,
            post_focus_wait=post_wait,
            aggressive=True,
        )
    if not focused:
        return False, title, hwnd
    fg_after = win32gui.GetWindowText(win32gui.GetForegroundWindow()).strip()
    return True, fg_after or title, hwnd


def open_app(params: dict[str, Any]) -> dict[str, Any]:
    raw_name = str(params.get("name", "")).strip()
    if not raw_name:
        raise ValueError("未指定应用名称")

    keywords, process_images = _resolve_app_target(raw_name)
    reuse_if_open = bool(params.get("reuse_if_open", True))
    want_focus = bool(params.get("focus", True))
    startup_wait = _clamp_wait(params.get("startup_wait"), default=1.1, min_v=0.0, max_v=12.0)
    focus_timeout = _clamp_wait(params.get("focus_timeout"), default=10.0, min_v=1.0, max_v=20.0)
    settle_wait = _clamp_wait(params.get("settle_wait"), default=0.45, min_v=0.05, max_v=3.0)
    existing = _existing_app_windows(keywords, process_images)

    if existing and reuse_if_open:
        focus_api_ok = False
        click_edit = _is_notepad_app(raw_name)
        if want_focus:
            focus_api_ok = _focus_window(
                keywords,
                process_images,
                timeout=focus_timeout,
                click_center=click_edit,
                app_for_click=raw_name,
                post_focus_wait=settle_wait,
                aggressive=True,
            )
        titles = [title for _, title, _ in existing]
        focus_info = _finalize_open_focus(
            raw_name,
            keywords,
            process_images,
            focus_attempted=want_focus,
            focus_api_ok=focus_api_ok,
        )
        return {
            "opened": raw_name,
            "launched": False,
            "already_running": True,
            "matching_windows": titles,
            "window_count": len(existing),
            **focus_info,
            "focus_requested": want_focus,
            "startup_wait": startup_wait,
            "focus_timeout": focus_timeout,
            "login_screen_detected": _login_screen_detected(
                titles, keywords, process_images, focus_info["focused_window"]
            ),
        }

    argv, launch_keywords, launch_proc = _launch_target(raw_name)
    if launch_proc and not process_images:
        process_images = launch_proc
    if launch_keywords and not keywords:
        keywords = launch_keywords

    subprocess.Popen(argv, shell=False)

    focus_api_ok = False
    click_edit = _is_notepad_app(raw_name)
    if want_focus:
        time.sleep(startup_wait)
        focus_api_ok = _focus_window(
            keywords,
            process_images,
            timeout=focus_timeout,
            click_center=click_edit,
            app_for_click=raw_name,
            post_focus_wait=settle_wait,
            aggressive=True,
        )
        if not focus_api_ok:
            # 某些应用窗口晚于进程可见，二次补偿
            time.sleep(0.5)
            focus_api_ok = _focus_window(
                keywords,
                process_images,
                timeout=max(2.0, focus_timeout * 0.6),
                click_center=click_edit,
                app_for_click=raw_name,
                post_focus_wait=settle_wait,
                aggressive=True,
            ) or focus_api_ok

    after = _existing_app_windows(keywords, process_images)
    titles = [title for _, title, _ in after]
    focus_info = _finalize_open_focus(
        raw_name,
        keywords,
        process_images,
        focus_attempted=want_focus,
        focus_api_ok=focus_api_ok,
    )
    return {
        "opened": raw_name,
        "launch": argv[-1],
        "launched": True,
        "already_running": False,
        "matching_windows": titles,
        "window_count": len(after),
        **focus_info,
        "focus_requested": want_focus,
        "startup_wait": startup_wait,
        "focus_timeout": focus_timeout,
        "login_screen_detected": _login_screen_detected(
            titles, keywords, process_images, focus_info["focused_window"]
        ),
    }


def focus_window(params: dict[str, Any]) -> dict[str, Any]:
    title = str(params.get("title") or params.get("name") or "").strip()
    if not title:
        raise ValueError("未指定窗口 title/name")
    keywords, process_images = _resolve_app_target(title)
    timeout = _clamp_wait(params.get("timeout"), default=6.0, min_v=1.0, max_v=20.0)
    settle_wait = _clamp_wait(params.get("settle_wait"), default=0.35, min_v=0.05, max_v=3.0)
    click_center = bool(params.get("click_center", False))
    if not _focus_window(
        keywords,
        process_images,
        timeout=timeout,
        click_center=click_center,
        post_focus_wait=settle_wait,
    ):
        raise RuntimeError(f"未找到窗口: {title}")
    return {
        "focused": title,
        "keywords": list(keywords),
        "timeout": timeout,
        "settle_wait": settle_wait,
    }


def _focus_via_alt_tab(target_hwnd: int, *, max_switches: int = 20) -> bool:
    """Alt+Tab 切换到目标 HWND（Win32 置前失败时的兜底）."""
    import win32api
    import win32con
    import win32gui

    if not win32gui.IsWindow(target_hwnd):
        return False
    if _foreground_matches_hwnd(target_hwnd):
        return True
    win32api.keybd_event(_VK["alt"], 0, 0, 0)
    try:
        for _ in range(max(1, max_switches)):
            _press_vk(_VK["tab"])
            time.sleep(0.14)
            if _foreground_matches_hwnd(target_hwnd):
                return True
        return _foreground_matches_hwnd(target_hwnd)
    finally:
        win32api.keybd_event(_VK["alt"], 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.06)


def _resolve_close_target(params: dict[str, Any]) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    raw = str(params.get("name") or params.get("title") or "").strip()
    if not raw:
        raise ValueError("未指定要关闭的应用 name/title")
    try:
        keywords, process_images = _resolve_app_target(raw)
        return raw, keywords, process_images
    except ValueError:
        return raw, _title_keywords(raw), ()


def close_app(params: dict[str, Any]) -> dict[str, Any]:
    """关闭目标窗口：优先 WM_CLOSE（免 Alt+Tab），失败再轻量置前后 Alt+F4."""
    import win32con
    import win32gui

    raw, keywords, process_images = _resolve_close_target(params)
    timeout = float(params.get("timeout", 6.0))
    hwnd = _find_window_hwnd(keywords, process_images, timeout=timeout)
    if not hwnd:
        raise RuntimeError(f"未找到要关闭的窗口: {raw}")

    window_title = win32gui.GetWindowText(hwnd).strip()

    if _close_hwnd_quiet(hwnd):
        return {
            "closed": raw,
            "window_title": window_title,
            "method": "wm_close",
            "still_visible": False,
            "success": True,
        }

    focus_method = "hwnd"
    if not _focus_hwnd(hwnd, aggressive=False, post_focus_wait=0.15):
        focus_method = "alt_tab"
        if not _focus_via_alt_tab(hwnd, max_switches=6):
            raise RuntimeError(f"无法切换到目标窗口: {raw}")

    time.sleep(0.1)
    closed = False
    close_method = f"{focus_method}_wm_close"
    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        time.sleep(0.35)
        closed = not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd)
    except Exception:
        closed = False
    if not closed and win32gui.IsWindow(hwnd):
        close_method = f"{focus_method}_alt_f4"
        _hotkey_names("alt", "f4")
        time.sleep(0.45)
        closed = not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd)

    still_open = win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd)
    return {
        "closed": raw,
        "window_title": window_title,
        "method": close_method,
        "still_visible": still_open,
        "success": not still_open,
    }


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
    keywords, process_images = _resolve_app_target(title)
    hwnd = _find_window_hwnd(keywords, process_images)
    if not hwnd:
        raise RuntimeError(f"未找到窗口: {title}")
    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    return {"minimized": title}


def maximize_window(params: dict[str, Any]) -> dict[str, Any]:
    import win32con
    import win32gui

    title = str(params.get("title") or params.get("name") or "").strip()
    keywords, process_images = _resolve_app_target(title)
    hwnd = _find_window_hwnd(keywords, process_images)
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
    """向前台窗口输入；默认假定 open_app 已置前，发剪贴板+Ctrl+V 或 write."""
    text = params.get("text", "")
    if not text:
        raise ValueError("text 不能为空")

    import win32gui

    pre_wait = _clamp_wait(params.get("pre_wait"), default=0.12, min_v=0.0, max_v=5.0)
    post_wait = _clamp_wait(params.get("post_wait"), default=0.15, min_v=0.0, max_v=5.0)
    app = str(params.get("app") or "").strip()

    if app:
        if _is_notepad_app(app):
            ok, fg_title, _ = ensure_app_focus_for_input(
                app, click_edit=True, aggressive=False, post_wait=max(pre_wait, 0.15)
            )
            if not ok:
                ensure_app_focus_for_input(app, click_edit=True, aggressive=True, post_wait=0.18)
        else:
            _nudge_app_focus(app)

    foreground = win32gui.GetWindowText(win32gui.GetForegroundWindow()).strip()
    time.sleep(pre_wait if not app or not _is_notepad_app(app) else 0.08)

    if any(ord(ch) > 127 for ch in text):
        _paste_text(text)
        method = "paste"
    else:
        pyautogui.write(text, interval=0.02)
        method = "write"
    time.sleep(post_wait)

    foreground_final = win32gui.GetWindowText(win32gui.GetForegroundWindow()).strip()
    return {
        "typed_length": len(text),
        "method": method,
        "text": text,
        "foreground_window": foreground_final or foreground,
        "app_requested": app or None,
        "pre_wait": pre_wait,
        "post_wait": post_wait,
    }


def _commit_save_dialog(target: Path) -> bool:
    """另存为：全选 → 粘贴完整路径 → 回车."""
    pyperclip.copy(str(target))
    time.sleep(0.12)
    _hotkey_names("ctrl", "a")
    time.sleep(0.06)
    _hotkey_names("ctrl", "v")
    time.sleep(0.12)
    _hotkey_names("enter")
    time.sleep(1.2)
    if target.is_file():
        return True
    _hotkey_names("enter")
    time.sleep(0.8)
    return target.is_file()


def save_notepad(params: dict[str, Any]) -> dict[str, Any]:
    """记事本 Ctrl+S → 填路径 → 回车（发快捷键前可 nudge 置前）."""
    target = _resolve_notepad_save_path(params)

    app = str(params.get("app") or "notepad").strip()
    if app:
        _nudge_app_focus(app)
        time.sleep(0.15)

    _hotkey_names("ctrl", "s")
    time.sleep(1.6)
    saved = _commit_save_dialog(target)
    size = target.stat().st_size if target.is_file() else 0
    return {
        "saved_path": str(target),
        "filename": target.name,
        "file_exists": saved,
        "file_size": size,
        "method": "ctrl_s_paste_path",
    }


def notepad_type_save(params: dict[str, Any]) -> dict[str, Any]:
    """记事本：Python 写入磁盘 → 打开文件 → 可选 Ctrl+S → 可选关闭（默认关闭）."""
    text = str(params.get("text", "")).strip()
    if not text:
        raise ValueError("text 不能为空")
    raw_name = str(params.get("filename") or params.get("path") or "note.txt").strip() or "note.txt"
    target = _resolve_notepad_save_path({"filename": raw_name, "path": raw_name})
    do_open = bool(params.get("open", True))
    do_save = bool(params.get("save", False))
    do_close = bool(params.get("close", True))

    target.write_text(text, encoding="utf-8")
    if not target.is_file() or target.stat().st_size <= 0:
        raise RuntimeError("正文未能写入目标文件")

    open_out: dict[str, Any] | None = None
    hwnd: int | None = None
    if do_open:
        open_out = _open_notepad_with_file(target)
        hwnd = int(open_out.get("hwnd") or 0) or None
        time.sleep(0.25)

    if do_save and hwnd:
        if _focus_hwnd(hwnd, aggressive=False, post_focus_wait=0.1):
            _hotkey_names("ctrl", "s")
            time.sleep(0.35)

    closed = False
    close_method = ""
    if do_close:
        if hwnd:
            closed = _close_hwnd_quiet(hwnd)
            close_method = "wm_close" if closed else "close_failed"
        else:
            close_out = close_app({"name": "notepad"})
            closed = bool(close_out.get("success"))
            close_method = str(close_out.get("method") or "")

    return {
        "text": text,
        "opened": do_open,
        "open": open_out,
        "saved": True,
        "closed": closed,
        "close_method": close_method,
        "typed_length": len(text),
        "method": "write_open_close",
        "saved_path": str(target),
        "filename": target.name,
        "file_exists": True,
        "file_size": target.stat().st_size,
    }


def wechat_send_message(params: dict[str, Any]) -> dict[str, Any]:
    """微信：置前 → Ctrl+F 搜联系人 → 进会话 → 粘贴 → 回车发送."""
    return _im_send_message("微信", params)


_IM_SEND_TIMING: dict[str, dict[str, float]] = {
    "微信": {"search_wait": 0.55, "chat_wait": 0.40},
}


def _im_send_timing(app: str) -> dict[str, float]:
    return _IM_SEND_TIMING.get(app.strip()) or _IM_SEND_TIMING.get(app.strip().lower()) or _IM_SEND_TIMING["微信"]


def _im_ctrl_f_search(app: str, hwnd: int) -> None:
    """微信：置前后 Ctrl+F 打开搜索框."""
    if not _foreground_matches_hwnd(hwnd):
        _focus_hwnd(hwnd, aggressive=True, post_focus_wait=0.2)
    if not foreground_is_app(app):
        raise RuntimeError(f"无法将{app}置于前台，请缩小 Hub 窗口后重试")
    _hotkey_chord(_VK["ctrl"], ord("F"))


def _im_open_search(app: str, hwnd: int) -> str:
    """打开 IM 搜索框（微信 Ctrl+F）."""
    _im_ctrl_f_search(app, hwnd)
    return "ctrl_f"


def _focus_im_hwnd(app: str) -> tuple[int, str]:
    """置前 IM 主窗口并返回 hwnd."""
    keywords, process_images = _resolve_app_target(app)
    best = _pick_best_window(_existing_app_windows(keywords, process_images), app=app)
    if not best:
        raise RuntimeError(f"未检测到{app}窗口，请先在桌面打开并登录{app}后再试")
    hwnd, title = best
    if not _focus_hwnd(
        hwnd,
        aggressive=True,
        click_center=False,
        app_for_click=app,
        post_focus_wait=0.25,
    ):
        raise RuntimeError(f"无法将{app}置于前台，请确认已打开并登录")
    if not foreground_is_app(app):
        raise RuntimeError(f"无法将{app}置于前台，请缩小 Hub 窗口后重试")
    return hwnd, title or ""


def _im_send_message(app: str, params: dict[str, Any]) -> dict[str, Any]:
    contact = str(params.get("contact") or params.get("name") or "").strip()
    message = str(params.get("message") or params.get("text") or "").strip()
    if not contact:
        raise ValueError("contact 不能为空")
    if not message:
        raise ValueError("message 不能为空")

    try:
        from sensehub.perception.virtual_session import VirtualScreenSession

        if VirtualScreenSession.is_active():
            VirtualScreenSession.suspend_automation(12.0)
    except Exception:
        pass

    do_send = bool(params.get("send", True))
    do_open = bool(params.get("open", False))
    timing = _im_send_timing(app)
    search_wait = _clamp_wait(params.get("search_wait"), default=timing["search_wait"], min_v=0.2, max_v=3.0)
    chat_wait = _clamp_wait(params.get("chat_wait"), default=timing["chat_wait"], min_v=0.15, max_v=3.0)

    keywords, process_images = _resolve_app_target(app)
    existing = _existing_app_windows(keywords, process_images)
    if not existing:
        raise RuntimeError(f"未检测到{app}窗口，请先在桌面打开并登录{app}后再试")

    open_out: dict[str, Any] | None = None

    if do_open:
        open_out = open_app({"name": app, "focus": True, "reuse_if_open": True})
        time.sleep(0.25)

    hwnd, focused_title = _focus_im_hwnd(app)
    search_step = _im_open_search(app, hwnd)
    time.sleep(0.2)
    _paste_text(contact)
    time.sleep(search_wait)
    _press_vk(_VK["enter"])
    time.sleep(chat_wait)
    _paste_text(message)
    time.sleep(0.04)

    sent = False
    if do_send:
        _press_vk(_VK["enter"])
        sent = True
        time.sleep(0.04)

    if not focused_title:
        import win32gui

        focused_title = win32gui.GetWindowText(win32gui.GetForegroundWindow()).strip()

    flow = [
        "focus",
        search_step,
        "paste_contact",
        "enter_chat",
        "paste_message",
        "enter_send" if sent else "skip_send",
    ]

    return {
        "app": app,
        "contact": contact,
        "message": message,
        "sent": sent,
        "method": "ctrl_f_search_paste_send",
        "flow": flow,
        "target_window": focused_title,
        "foreground_window": focused_title,
        "open": open_out,
    }


def _primary_app_from_steps(steps: list[Any]) -> str | None:
    for step in reversed(steps):
        tool = getattr(step, "tool", None) or (step.get("tool") if isinstance(step, dict) else None)
        params = getattr(step, "params", None) or (step.get("params") if isinstance(step, dict) else {}) or {}
        if tool == "open_app":
            name = str(params.get("name", "")).strip()
            if name:
                return name
        if tool == "notepad_type_save":
            return "notepad"
        if tool == "wechat_send_message":
            return "微信"
        if tool == "type_text":
            app = str(params.get("app", "")).strip()
            if app:
                return app
    return None


def schedule_refocus_from_steps(steps: list[Any], *, delay: float = 0.45) -> None:
    """Hub 网页在请求返回后常会抢回焦点；延迟再次把目标应用置前."""
    for step in reversed(steps):
        tool = getattr(step, "tool", None) or (step.get("tool") if isinstance(step, dict) else None)
        if tool == "wechat_send_message":
            return
        if tool == "notepad_type_save":
            params = getattr(step, "params", None) or (step.get("params") if isinstance(step, dict) else {}) or {}
            if params.get("close", True):
                return
            break
        break

    name = _primary_app_from_steps(steps)
    if not name:
        return

    def _run() -> None:
        time.sleep(delay)
        try:
            ensure_app_focus_for_input(
                name,
                click_edit=False,
                aggressive=True,
                timeout=5.0,
                post_wait=0.2,
            )
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
