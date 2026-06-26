"""积分游戏化 API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from sensehub.api.deps import get_current_user
from sensehub.db import gamification as game_store

router = APIRouter(tags=["gamification"])


class ProfileUpdate(BaseModel):
    profile_bg: str | None = None
    profile_theme: str | None = None


class AchievementShareRequest(BaseModel):
    origin: str = Field(default="", max_length=256)


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


@router.post("/gamification/achievements/{achievement_id}/share")
async def gamification_achievement_share(
    achievement_id: str,
    body: AchievementShareRequest,
    username: str = Depends(get_current_user),
):
    try:
        return game_store.create_achievement_share(username, achievement_id, origin=body.origin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/gamification/share/achievement/{token}")
async def gamification_achievement_share_public(token: str):
    try:
        return game_store.get_achievement_share_public(token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/gamification/share/achievement/{token}/card.png")
async def gamification_achievement_share_card(
    token: str,
    request: Request,
    origin: str = Query(""),
):
    base = (origin or "").strip().rstrip("/") or str(request.headers.get("origin") or "").strip().rstrip("/")
    if base and not base.startswith(("http://", "https://")):
        base = f"http://{base}"
    share_url = f"{base}/share/achievement/{token}" if base else ""
    try:
        png = game_store.render_achievement_share_card_png(token, share_url=share_url)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})
