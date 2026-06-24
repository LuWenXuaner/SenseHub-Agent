"""工具基类：标准化接口、统一返回、重试、审计、Kill Switch."""

from __future__ import annotations

import functools
import time
from typing import Any, Callable

from sensehub.execution.kill_switch import is_killed
from sensehub.security.audit import log_audit


def tool_result(
    success: bool,
    message: str = "",
    data: dict[str, Any] | None = None,
    error: str | None = None,
    screenshot_path: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "success": success,
        "message": message,
        "data": data or {},
    }
    if error:
        result["error"] = error
    if screenshot_path:
        result["screenshot_path"] = screenshot_path
    return result


def safe_execute(
    tool_name: str,
    fn: Callable[[dict[str, Any]], dict[str, Any]],
    params: dict[str, Any],
    risk_level: str = "L1",
    max_retries: int = 2,
    audit_input: str = "",
) -> dict[str, Any]:
    if is_killed():
        return tool_result(False, "Kill Switch 已激活，所有工具调用已暂停", error="kill_switch_triggered")

    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            output = fn(params)
            if isinstance(output, dict) and "success" not in output:
                output = tool_result(True, data=output)
            log_audit(
                input_text=audit_input or tool_name,
                action=tool_name,
                risk_level=risk_level,
                result="ok",
            )
            return output
        except Exception as exc:
            last_error = str(exc)
            if attempt < max_retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            log_audit(
                input_text=audit_input or tool_name,
                action=tool_name,
                risk_level=risk_level,
                result=f"error: {last_error}",
            )
            return tool_result(False, f"{tool_name} 执行失败: {last_error}", error=last_error)


def with_retry(
    max_retries: int = 2,
    delay: float = 1.0,
    tool_name: str = "",
    risk_level: str = "L1",
):
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(params: dict[str, Any]) -> dict[str, Any]:
            name = tool_name or fn.__name__
            return safe_execute(
                name, fn, params,
                risk_level=risk_level,
                max_retries=max_retries,
            )
        return wrapper
    return decorator


def push_progress(message: str, progress: float = 0.0) -> None:
    try:
        from sensehub.orchestration.notify import push_event
        push_event("tool_progress", {"message": message, "progress": progress})
    except Exception:
        pass
