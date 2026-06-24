"""剪贴板读写."""

from __future__ import annotations

from typing import Any

import pyperclip


def get_clipboard(params: dict[str, Any]) -> dict[str, Any]:
    text = pyperclip.paste()
    return {"text": text, "length": len(text or "")}


def set_clipboard(params: dict[str, Any]) -> dict[str, Any]:
    text = params.get("text", "")
    pyperclip.copy(text)
    return {"text": text, "length": len(text)}
