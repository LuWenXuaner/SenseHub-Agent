"""虚拟屏 API（Phase 4）."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException

from sensehub.api.deps import get_current_user
from sensehub.licensing.tier import feature_enabled
from sensehub.perception.gesture import GestureDetector
from sensehub.perception.virtual_screen import (
    get_calibration,
    map_camera_to_virtual_click,
    save_calibration,
)

router = APIRouter(tags=["virtual-screen"])


class CalibrationBody(BaseModel):
    screen_points: list[list[float]]
    camera_points: list[list[float]]


@router.get("/virtual-screen/calibration")
async def read_calibration(_: str = Depends(get_current_user)):
    if not feature_enabled("virtual_screen"):
        raise HTTPException(status_code=403, detail="虚拟屏需要 Max 档位")
    return get_calibration()


@router.post("/virtual-screen/calibration")
async def write_calibration(body: CalibrationBody, _: str = Depends(get_current_user)):
    if not feature_enabled("virtual_screen"):
        raise HTTPException(status_code=403, detail="虚拟屏需要 Max 档位")
    try:
        return save_calibration(body.screen_points, body.camera_points)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/virtual-screen/air-click")
async def air_click(_: str = Depends(get_current_user)):
    if not feature_enabled("virtual_screen"):
        raise HTTPException(status_code=403, detail="虚拟屏需要 Max 档位")
    from sensehub.perception.camera import CameraService

    cam = CameraService.get()
    if not cam.running:
        cam.start()
    frame = cam.read()
    if frame is None:
        raise HTTPException(status_code=400, detail="无法读取摄像头")
    tip = GestureDetector.get().fingertip_for_virtual_screen(frame)
    if not tip:
        raise HTTPException(status_code=400, detail="未检测到手部")
    try:
        return map_camera_to_virtual_click(tip[0], tip[1])
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
