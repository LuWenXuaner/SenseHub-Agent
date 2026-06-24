"""积分游戏化 API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException

from sensehub.api.deps import get_current_user
from sensehub.db import gamification as game_store

router = APIRouter(tags=["gamification"])


class ProfileUpdate(BaseModel):
    profile_bg: str | None = None
    profile_theme: str | None = None


@router.get("/gamification")
async def gamification_summary(username: str = Depends(get_current_user)):
    try:
        return game_store.get_engagement_summary(username)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/gamification/leaderboard")
async def gamification_leaderboard(limit: int = 20, username: str = Depends(get_current_user)):
    _ = username
    return {"items": game_store.leaderboard(limit=limit)}


@router.get("/gamification/wheel")
async def gamification_wheel(username: str = Depends(get_current_user)):
    try:
        return game_store.wheel_status(username)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/gamification/wheel/spin")
async def gamification_wheel_spin(username: str = Depends(get_current_user)):
    try:
        return game_store.spin_wheel(username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/gamification/profile")
async def gamification_profile(body: ProfileUpdate, username: str = Depends(get_current_user)):
    try:
        return game_store.update_profile(
            username,
            profile_bg=body.profile_bg,
            profile_theme=body.profile_theme,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
