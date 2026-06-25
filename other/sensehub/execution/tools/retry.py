"""工具重试装饰器."""

from __future__ import annotations

import functools
import time
from typing import Any, Callable

from sensehub.execution.tool_result import ToolResult


def retry(max_attempts: int = 2, delay: float = 0.5, backoff: float = 2.0) -> Callable:
    """重试装饰器：仅在返回 ToolResult(success=False) 时重试."""
    def decorator(fn: Callable[..., ToolResult]) -> Callable[..., ToolResult]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> ToolResult:
            last_result = fn(*args, **kwargs)
            for attempt in range(1, max_attempts):
                if last_result.success:
                    return last_result
                time.sleep(delay * (backoff ** (attempt - 1)))
                last_result = fn(*args, **kwargs)
            return last_result
        return wrapper
    return decorator
