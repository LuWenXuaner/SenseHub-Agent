"""感知 API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sensehub.api.deps import get_current_user
from sensehub.models.perception_schemas import CameraStatus, PerceptionEvent
from sensehub.perception.camera import CameraService
from sensehub.perception.detector import YoloDetector
from sensehub.perception.device import inference_device_label
from sensehub.perception.events import list_events
from sensehub.settings import get_settings

router = APIRouter(tags=["perception"])


@router.get("/perception/status", response_model=CameraStatus)
async def perception_status(_: str = Depends(get_current_user)):
    cam = CameraService.get()
    det = YoloDetector.get()
    settings = get_settings()
    return CameraStatus(
        running=cam.running,
        camera_index=cam.camera_index(),
        detector_ready=det.ready,
        yolo_weights=det.weights_path,
        inference_device=inference_device_label() if det.ready else inference_device_label(),
        last_error=cam.last_error or det.load_error,
    )


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
    CameraService.get().stop()
    return await perception_status(_)


@router.get("/perception/events", response_model=list[PerceptionEvent])
async def perception_events(_: str = Depends(get_current_user), limit: int = 50):
    return list_events(limit=limit)
