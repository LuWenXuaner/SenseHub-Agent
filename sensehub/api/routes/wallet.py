"""积分、邀请、插件、账单 API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from sensehub.api.deps import get_current_user
from sensehub.db import wallet as wallet_store
from sensehub.util.qr_png import qr_png_bytes

router = APIRouter(tags=["wallet"])


class RedeemRequest(BaseModel):
    item_id: str


class SubscribeRequest(BaseModel):
    plan: str = "pro"


class PluginToggleRequest(BaseModel):
    enabled: bool


@router.get("/wallet/plans")
async def wallet_plans():
    return {"items": wallet_store.list_subscription_plans()}


@router.get("/wallet")
async def wallet_summary(username: str = Depends(get_current_user)):
    try:
        return wallet_store.get_summary(username)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/wallet/checkin")
async def wallet_checkin(username: str = Depends(get_current_user)):
    try:
        return wallet_store.check_in(username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/wallet/ledger")
async def wallet_ledger(filter: str = "all", username: str = Depends(get_current_user)):
    return {"items": wallet_store.list_ledger(username, filter_type=filter)}


@router.get("/wallet/exchanges")
async def wallet_exchanges(username: str = Depends(get_current_user)):
    return {"items": wallet_store.list_exchanges(username)}


@router.post("/wallet/redeem")
async def wallet_redeem(body: RedeemRequest, username: str = Depends(get_current_user)):
    try:
        return wallet_store.redeem_item(username, body.item_id.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/wallet/subscribe")
async def wallet_subscribe(body: SubscribeRequest, username: str = Depends(get_current_user)):
    try:
        return wallet_store.subscribe_plan(username, body.plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/wallet/bills")
async def wallet_bills(username: str = Depends(get_current_user)):
    return {
        "summary": wallet_store.bills_summary(username),
        "items": wallet_store.list_bills(username),
    }


@router.get("/wallet/token-usage")
async def wallet_token_usage(days: int = 30, username: str = Depends(get_current_user)):
    from sensehub.db import token_usage as token_usage_store

    return token_usage_store.token_usage_summary(username, days=days)


@router.get("/invites")
async def invites_overview(username: str = Depends(get_current_user)):
    return {
        "stats": wallet_store.invite_stats(username),
        "items": wallet_store.list_invites(username),
    }


@router.get("/invites/qrcode.png")
async def invites_qrcode_png(
    request: Request,
    origin: str = Query("", description="前端站点 origin，用于生成邀请链接"),
    username: str = Depends(get_current_user),
):
    stats = wallet_store.invite_stats(username)
    code = str(stats.get("invite_code") or "").strip()
    if not code:
        raise HTTPException(status_code=404, detail="邀请码不存在")
    base = (origin or "").strip().rstrip("/")
    if not base:
        base = str(request.headers.get("origin") or "").strip().rstrip("/")
    if not base:
        base = "http://127.0.0.1:5173"
    if not base.startswith(("http://", "https://")):
        base = f"http://{base}"
    link = f"{base}/login?invite={code}"
    try:
        png = qr_png_bytes(link)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "private, max-age=300"})


@router.get("/plugins")
async def plugins_list(username: str = Depends(get_current_user)):
    return {"items": wallet_store.list_plugins(username)}


@router.put("/plugins/{plugin_id}")
async def plugins_toggle(
    plugin_id: str,
    body: PluginToggleRequest,
    username: str = Depends(get_current_user),
):
    try:
        return wallet_store.set_plugin_enabled(username, plugin_id, body.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
