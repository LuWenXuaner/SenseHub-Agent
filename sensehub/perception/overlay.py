"""Windows 桌面透明虚拟鼠标 Overlay."""

from __future__ import annotations

import threading
import tkinter as tk
from queue import Empty, Queue

_OVERLAY_SIZE = 72


class VirtualMouseOverlay:
    """小窗跟随光标绘制虚拟鼠标，点击穿透，不遮挡整屏交互."""

    _instance: "VirtualMouseOverlay | None" = None

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._queue: Queue = Queue()
        self._running = False
        self._root: tk.Tk | None = None
        self._canvas: tk.Canvas | None = None
        self._cursor_id: int | None = None
        self._label_id: int | None = None
        self._screen_w = 1920
        self._screen_h = 1080

    @classmethod
    def get(cls) -> "VirtualMouseOverlay":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_tk, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._queue.put(("stop",))

    def update(self, x: float, y: float, *, clicked: bool = False) -> None:
        if not self._running:
            return
        self._queue.put(("move", float(x), float(y), bool(clicked)))

    @staticmethod
    def _hwnd(root: tk.Tk) -> int:
        hwnd = root.winfo_id()
        try:
            import ctypes

            parent = ctypes.windll.user32.GetParent(hwnd)
            return int(parent or hwnd)
        except Exception:
            return int(hwnd)

    def _run_tk(self) -> None:
        root = tk.Tk()
        root.withdraw()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.config(bg="#00FF00")
        root.wm_attributes("-transparentcolor", "#00FF00")

        self._screen_w = root.winfo_screenwidth()
        self._screen_h = root.winfo_screenheight()
        root.geometry(f"{_OVERLAY_SIZE}x{_OVERLAY_SIZE}+0+0")

        canvas = tk.Canvas(
            root,
            width=_OVERLAY_SIZE,
            height=_OVERLAY_SIZE,
            bg="#00FF00",
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(fill="both", expand=True)

        self._root = root
        self._canvas = canvas

        cx = _OVERLAY_SIZE // 2
        cy = _OVERLAY_SIZE // 2
        self._cursor_id = canvas.create_oval(cx - 11, cy - 11, cx + 11, cy + 11, outline="#6f7bff", width=3)
        self._label_id = canvas.create_text(
            cx, cy - 18, text="虚拟鼠标", fill="#6f7bff", font=("Microsoft YaHei", 9, "bold")
        )

        root.deiconify()
        self._make_click_through(root)
        self._pump()
        root.mainloop()

    def _make_click_through(self, root: tk.Tk) -> None:
        try:
            import win32con
            import win32gui

            hwnd = self._hwnd(root)
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            style |= (
                win32con.WS_EX_LAYERED
                | win32con.WS_EX_TRANSPARENT
                | win32con.WS_EX_TOPMOST
                | win32con.WS_EX_TOOLWINDOW
                | win32con.WS_EX_NOACTIVATE
            )
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
        except Exception:
            pass

    def _pump(self) -> None:
        if not self._root or not self._canvas:
            return
        if not self._running:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None
            self._canvas = None
            return

        try:
            while True:
                item = self._queue.get_nowait()
                if not item:
                    continue
                if item[0] == "stop":
                    self._running = False
                    break
                if item[0] == "move":
                    _tag, x, y, clicked = item
                    self._draw_cursor(float(x), float(y), bool(clicked))
        except Empty:
            pass

        self._root.after(16, self._pump)

    def _draw_cursor(self, x: float, y: float, clicked: bool) -> None:
        if not self._root or not self._canvas or self._cursor_id is None or self._label_id is None:
            return

        half = _OVERLAY_SIZE // 2
        left = max(0, min(int(x) - half, self._screen_w - _OVERLAY_SIZE))
        top = max(0, min(int(y) - half, self._screen_h - _OVERLAY_SIZE))
        self._root.geometry(f"{_OVERLAY_SIZE}x{_OVERLAY_SIZE}+{left}+{top}")

        cx = int(x) - left
        cy = int(y) - top
        color = "#22c55e" if clicked else "#6f7bff"
        self._canvas.coords(self._cursor_id, cx - 11, cy - 11, cx + 11, cy + 11)
        self._canvas.itemconfig(self._cursor_id, outline=color)
        self._canvas.coords(self._label_id, cx, cy - 18)
        self._canvas.itemconfig(self._label_id, fill=color)
