"""OpenClaw 风格 Agent 循环（兼容入口，实现已迁至 runtime）."""

from __future__ import annotations

from typing import Any

from sensehub.runtime.agent_runtime import AgentRuntime


async def run_agent_loop(
    user_text: str,
    *,
    history: list[dict[str, Any]] | None = None,
    intent_raw: dict[str, Any] | None = None,
    session_id: str = "",
    max_iterations: int = 15,
) -> dict[str, Any]:
    return await AgentRuntime.run(
        user_text,
        history=history,
        intent_raw=intent_raw,
        session_id=session_id,
        max_iterations=max_iterations,
    )
