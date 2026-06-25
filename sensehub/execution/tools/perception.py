"""感知工具：查询当前摄像头上下文."""

from __future__ import annotations

from typing import Any

from sensehub.perception.camera import CameraService
from sensehub.perception.context import PerceptionContext


def get_perception_state(params: dict[str, Any] | None = None) -> dict[str, Any]:
    _ = params
    cam = CameraService.get()
    ctx = PerceptionContext.get().to_tool_output()
    ctx["camera_running"] = cam.running
    return ctx
