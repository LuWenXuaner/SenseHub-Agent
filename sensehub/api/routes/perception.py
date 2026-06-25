"""感知 API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sensehub.api.deps import get_current_user
from sensehub.models.perception_schemas import CameraStatus, PerceptionEvent
from sensehub.perception.camera import CameraService
from sensehub.perception.config import get_perception_config, reload_perception_config
from sensehub.perception.context import PerceptionContext
from sensehub.perception.detector import YoloDetector
from sensehub.perception.device import inference_device_label
from sensehub.perception.events import list_events

router = APIRouter(tags=["perception"])


class PerceptionConfigPatch(BaseModel):
    detect_every_n_frames: int | None = Field(default=None, ge=1, le=30)
    gesture_every_n_frames: int | None = Field(default=None, ge=1, le=30)
    preview_interval_ms: int | None = Field(default=None, ge=50, le=500)
    camera_mirror: bool | None = None


@router.get("/perception/status", response_model=CameraStatus)
async def perception_status(_: str = Depends(get_current_user)):
    cam = CameraService.get()
    det = YoloDetector.get()
    return CameraStatus(
        running=cam.running,
        camera_index=cam.camera_index(),
        detector_ready=det.ready,
        yolo_weights=det.weights_path,
        inference_device=inference_device_label() if det.ready else inference_device_label(),
        last_error=cam.last_error or det.load_error,
    )


@router.get("/perception/config")
async def perception_config(_: str = Depends(get_current_user)) -> dict[str, Any]:
    return get_perception_config()


@router.patch("/perception/config")
async def patch_perception_config(body: PerceptionConfigPatch, _: str = Depends(get_current_user)) -> dict[str, Any]:
    import yaml

    from sensehub.settings import CONFIG_DIR

    path = CONFIG_DIR / "perception.yaml"
    raw: dict[str, Any] = {}
    if path.is_file():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    perc = dict(raw.get("perception") or {})
    for key, val in body.model_dump(exclude_none=True).items():
        perc[key] = val
    raw["perception"] = perc
    path.write_text(yaml.dump(raw, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    return reload_perception_config()


@router.get("/perception/context")
async def perception_context(_: str = Depends(get_current_user)) -> dict[str, Any]:
    return PerceptionContext.get().to_tool_output()


@router.post("/perception/camera/start", response_model=CameraStatus)
async def camera_start(_: str = Depends(get_current_user)):
    cam = CameraService.get()
    try:
        cam.start()
        YoloDetector.get().ensure_loaded()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await perception_status(_)


@router.post("/perception/camera/stop", response_model=CameraStatus)
async def camera_stop(_: str = Depends(get_current_user)):
    from sensehub.api.camera_broadcaster import camera_broadcaster
    from sensehub.perception.virtual_session import VirtualScreenSession

    if VirtualScreenSession.is_active():
        return await perception_status(_)
    await camera_broadcaster.stop_if_idle()
    if camera_broadcaster.client_count == 0:
        VirtualScreenSession._release_camera_if_idle()
    return await perception_status(_)


@router.get("/perception/events", response_model=list[PerceptionEvent])
async def perception_events(_: str = Depends(get_current_user), limit: int = 50):
    return list_events(limit=limit)
