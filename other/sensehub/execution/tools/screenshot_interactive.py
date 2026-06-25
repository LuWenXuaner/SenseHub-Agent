"""交互式区域截图：全屏覆盖层 + 鼠标拖拽选择区域后截图。"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from typing import Any

import mss
from PIL import Image

from sensehub.execution.tools.base import tool_result
from sensehub.settings import get_settings


class _RegionSelector:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.3)
        self.root.configure(bg="black", cursor="crosshair")

        self.canvas = tk.Canvas(self.root, highlightthickness=0, cursor="crosshair", bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._start_x: int | None = None
        self._start_y: int | None = None
        self._rect_id: int | None = None
        self._dim_id: int | None = None
        self.region: tuple[int, int, int, int] | None = None

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind("<Escape>", self._on_cancel)

    def _on_press(self, event: tk.Event) -> None:
        self._start_x = event.x
        self._start_y = event.y
        for tid in (self._rect_id, self._dim_id):
            if tid:
                self.canvas.delete(tid)

    def _on_drag(self, event: tk.Event) -> None:
        if self._start_x is None or self._start_y is None:
            return
        for tid in (self._rect_id, self._dim_id):
            if tid:
                self.canvas.delete(tid)
        self._rect_id = self.canvas.create_rectangle(
            self._start_x, self._start_y, event.x, event.y,
            outline="#00FF00", width=2,
        )
        w = abs(event.x - self._start_x)
        h = abs(event.y - self._start_y)
        label_x = (self._start_x + event.x) // 2
        label_y = min(self._start_y, event.y) - 12
        self._dim_id = self.canvas.create_text(
            label_x, label_y,
            text=f"{w} × {h}", fill="#00FF00",
            font=("Consolas", 14, "bold"),
            anchor="s",
        )

    def _on_release(self, event: tk.Event) -> None:
        if self._start_x is None or self._start_y is None:
            return
        x1, y1 = self._start_x, self._start_y
        x2, y2 = event.x, event.y
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        if width >= 10 and height >= 10:
            self.region = (left, top, width, height)
        self.root.quit()
        self.root.destroy()

    def _on_cancel(self, event: tk.Event) -> None:
        self.region = None
        self.root.quit()
        self.root.destroy()

    def select(self) -> tuple[int, int, int, int] | None:
        self.root.mainloop()
        return self.region


def capture_interactive_region(params: dict[str, Any]) -> dict[str, Any]:
    """鼠标拖拽选择区域后截图。"""
    selector = _RegionSelector()
    region = selector.select()

    if not region:
        return tool_result(False, "用户取消了区域选择")

    left, top, width, height = region
    settings = get_settings()
    out_dir = settings.screenshots_dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = out_dir / f"region_{timestamp}.png"
    out_dir.mkdir(parents=True, exist_ok=True)

    with mss.mss() as sct:
        monitor = {"left": left, "top": top, "width": width, "height": height}
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    img.save(path)

    return tool_result(True, f"交互区域截图已保存: {path}", data={
        "screenshot_path": str(path),
        "mode": "interactive_region",
        "left": left,
        "top": top,
        "width": width,
        "height": height,
    })
