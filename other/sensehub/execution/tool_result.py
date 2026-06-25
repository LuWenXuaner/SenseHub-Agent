"""标准化工具返回结构."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    success: bool
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    screenshot_path: str | None = None
    duration_ms: int = 0


def ok(message: str = "", **data: Any) -> ToolResult:
    return ToolResult(success=True, message=message, data=data)


def fail(error: str, message: str = "") -> ToolResult:
    return ToolResult(success=False, message=message or error, error=error)
