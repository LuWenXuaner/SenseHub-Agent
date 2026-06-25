"""OS-level mouse pointer control for virtual screen."""

from __future__ import annotations

import logging
import sys
import time

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    _INPUT_MOUSE = 0
    _MOUSEEVENTF_LEFTDOWN = 0x0002
    _MOUSEEVENTF_LEFTUP = 0x0004


def get_cursor_position() -> tuple[int, int]:
    if sys.platform == "win32":
        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return int(pt.x), int(pt.y)
    import pyautogui

    pos = pyautogui.position()
    return int(pos.x), int(pos.y)


def move_pointer(x: float, y: float) -> None:
    ix, iy = int(round(x)), int(round(y))
    if sys.platform == "win32":
        ctypes.windll.user32.SetCursorPos(ix, iy)
        return
    import pyautogui

    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    pyautogui.moveTo(ix, iy, duration=0)


def _win32_sendinput_click() -> bool:
    inp_down = INPUT(type=_INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, _MOUSEEVENTF_LEFTDOWN, 0, 0))
    inp_up = INPUT(type=_INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, _MOUSEEVENTF_LEFTUP, 0, 0))
    batch = (INPUT * 2)(inp_down, inp_up)
    sent = ctypes.windll.user32.SendInput(2, ctypes.byref(batch), ctypes.sizeof(INPUT))
    return sent == 2


def _win32_mouse_event_click(ix: int, iy: int, *, move: bool = True) -> None:
    import win32api
    import win32con

    if move:
        win32api.SetCursorPos((ix, iy))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.04)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def _win32_postmessage_click(ix: int, iy: int) -> bool:
    """向光标下窗口投递 WM_LBUTTON*，浏览器/桌面控件更认这个."""
    import win32api
    import win32con
    import win32gui

    hwnd = win32gui.WindowFromPoint((ix, iy))
    if not hwnd:
        return False
    try:
        cx, cy = win32gui.ScreenToClient(hwnd, (ix, iy))
        lparam = win32api.MAKELONG(int(cx) & 0xFFFF, int(cy) & 0xFFFF)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(0.04)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)
        return True
    except Exception:
        return False


def click_at_cursor() -> bool:
    """在当前光标位置点击，优先硬件注入（避免 PostMessage 打到 overlay）."""
    ix, iy = get_cursor_position()

    if sys.platform == "win32":
        try:
            _win32_mouse_event_click(ix, iy, move=False)
            return True
        except Exception as exc:
            logger.debug("mouse_event click at cursor failed: %s", exc)
        try:
            if _win32_sendinput_click():
                return True
        except Exception as exc:
            logger.debug("SendInput click at cursor failed: %s", exc)
        try:
            if _win32_postmessage_click(ix, iy):
                return True
        except Exception as exc:
            logger.debug("PostMessage click at cursor failed: %s", exc)

    import pyautogui

    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    pyautogui.mouseDown(ix, iy, button="left")
    time.sleep(0.05)
    pyautogui.mouseUp(ix, iy, button="left")
    return True


def click_pointer(x: float, y: float, *, move: bool = True) -> bool:
    """定位光标并点击；返回是否至少一种注入方式已执行."""
    ix, iy = int(round(x)), int(round(y))
    if move:
        move_pointer(ix, iy)
        time.sleep(0.06)

    if sys.platform == "win32":
        try:
            if _win32_postmessage_click(ix, iy):
                return True
        except Exception as exc:
            logger.debug("PostMessage click failed: %s", exc)
        try:
            _win32_mouse_event_click(ix, iy, move=move)
            return True
        except Exception as exc:
            logger.debug("mouse_event click failed: %s", exc)
        try:
            if _win32_sendinput_click():
                return True
        except Exception as exc:
            logger.debug("SendInput click failed: %s", exc)

    import pyautogui

    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    if move:
        pyautogui.moveTo(ix, iy, duration=0)
    pyautogui.mouseDown(ix, iy, button="left")
    time.sleep(0.05)
    pyautogui.mouseUp(ix, iy, button="left")
    return True
