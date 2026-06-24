"""任务完成 TTS 等反馈钩子."""

from __future__ import annotations

import asyncio

from sensehub.feedback.tts import speak
from sensehub.licensing.tier import feature_enabled
from sensehub.models.schemas import TaskResponse
from sensehub.settings import get_settings


def setup_feedback_hooks() -> None:
    from sensehub.orchestration.notify import subscribe

    subscribe(_on_task_update)


def _on_task_update(task: TaskResponse) -> None:
    if task.status != "done":
        return
    settings = get_settings()
    if not settings.tts_enabled or not feature_enabled("tts_feedback"):
        return
    summary = (task.summary or task.intent_text or "任务").strip()
    text = f"任务已完成，{summary[:40]}"
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(speak(text))
    except RuntimeError:
        pass
