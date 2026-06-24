"""安全中心 API（Phase 3）."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException

from sensehub.api.deps import get_current_user
from sensehub.licensing.tier import feature_enabled, get_tier
from sensehub.security.audit import list_audit
from sensehub.security.network import allow_lan_enabled, get_ip_whitelist, set_ip_whitelist
from sensehub.security.sandbox import add_runtime_grant, status_payload

router = APIRouter(tags=["security"])


class WhitelistBody(BaseModel):
    ips: list[str]


class SandboxGrantBody(BaseModel):
    path: str


@router.get("/security/status")
async def security_status(_: str = Depends(get_current_user)):
    return {
        "tier": get_tier(),
        "allow_lan": allow_lan_enabled(),
        "ip_whitelist": get_ip_whitelist(),
        "lan_access": feature_enabled("lan_access"),
    }


@router.put("/security/whitelist")
async def update_whitelist(body: WhitelistBody, _: str = Depends(get_current_user)):
    if not feature_enabled("lan_access"):
        raise HTTPException(status_code=403, detail="局域网白名单需要 Pro 档位")
    ips = set_ip_whitelist(body.ips)
    return {"ips": ips}


@router.get("/security/sandbox")
async def sandbox_status(_: str = Depends(get_current_user)):
    return status_payload()


@router.post("/security/sandbox/grant")
async def sandbox_grant(body: SandboxGrantBody, _: str = Depends(get_current_user)):
    path = body.path.strip()
    if not path:
        raise HTTPException(status_code=400, detail="path 不能为空")
    try:
        resolved = add_runtime_grant(path)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "path": str(resolved), **status_payload()}


@router.get("/security/audit-summary")
async def audit_summary(_: str = Depends(get_current_user), limit: int = 20):
    rows = list_audit(limit=limit)
    return {"count": len(rows), "recent": rows}
