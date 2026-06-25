"""虚拟屏 API（Phase 4）."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException

from sensehub.api.deps import get_current_user
from sensehub.licensing.tier import feature_enabled
from sensehub.perception.virtual_screen import get_calibration, save_calibration
from sensehub.perception.virtual_session import VirtualScreenSession

router = APIRouter(tags=["virtual-screen"])


class CalibrationBody(BaseModel):
    screen_points: list[list[float]]
    camera_points: list[list[float]]
    frame_width: int = 0
    frame_height: int = 0


@router.get("/virtual-screen/calib-grid")
async def read_calib_grid(_: str = Depends(get_current_user)):
    if not feature_enabled("virtual_screen"):
        raise HTTPException(status_code=403, detail="虚拟屏需要 Max 档位")
    from sensehub.perception.virtual_screen import calib_grid_screen_points

    return {"points": calib_grid_screen_points()}


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
        return save_calibration(
            body.screen_points,
            body.camera_points,
            frame_width=body.frame_width,
            frame_height=body.frame_height,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/virtual-screen/preview-map")
async def preview_map(_: str = Depends(get_current_user)):
    if not feature_enabled("virtual_screen"):
        raise HTTPException(status_code=403, detail="虚拟屏需要 Max 档位")
    from sensehub.perception.virtual_session import VirtualScreenSession

    try:
        return VirtualScreenSession.preview_mapped_point()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/virtual-screen/air-click")
async def air_click(_: str = Depends(get_current_user)):
    if not feature_enabled("virtual_screen"):
        raise HTTPException(status_code=403, detail="虚拟屏需要 Max 档位")
    try:
        return VirtualScreenSession.air_click_at_fingertip()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
