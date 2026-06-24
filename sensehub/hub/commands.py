"""综合控制台本地指令已废弃：一律走 process_user_input + 工具."""

from __future__ import annotations


def handle_local_command(text: str) -> dict | None:
    """已废弃，始终返回 None。虚拟屏等请由规划脑调用 virtual_* 工具."""
    _ = text
    return None
