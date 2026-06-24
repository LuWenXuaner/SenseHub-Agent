"""屏幕截图."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import mss
from PIL import Image

from sensehub.settings import get_settings


def run(params: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    out_dir = settings.screenshots_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"shot_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
    path = out_dir / name

    mode = params.get("mode", "fullscreen")
    with mss.mss() as sct:
        if mode == "active_window":
            monitor = sct.monitors[1]
        else:
            monitor = sct.monitors[0]
        img = sct.grab(monitor)
        Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX").save(path)

    return {"screenshot_path": str(path), "mode": mode}
