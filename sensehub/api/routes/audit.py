from fastapi import APIRouter, Depends

from sensehub.api.deps import get_current_user
from sensehub.security.audit import list_audit

router = APIRouter(tags=["audit"])


@router.get("/audit")
async def audit_logs(_: str = Depends(get_current_user), limit: int = 100):
    return list_audit(limit=limit)
