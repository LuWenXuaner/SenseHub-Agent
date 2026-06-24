"""安全隧道占位（Phase 4 Max）."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sensehub.api.deps import get_current_user
from sensehub.licensing.tier import feature_enabled

router = APIRouter(tags=["tunnel"])


@router.get("/tunnel/status")
async def tunnel_status(_: str = Depends(get_current_user)):
    if not feature_enabled("secure_tunnel"):
        raise HTTPException(status_code=403, detail="安全隧道需要 Max 档位")
    return {
        "enabled": False,
        "status": "placeholder",
        "message": "Phase 4 占位：后续可接入 WireGuard/Cloudflare Tunnel",
    }
