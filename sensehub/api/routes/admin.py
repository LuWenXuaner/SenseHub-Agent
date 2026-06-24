"""管理员 API（仅 admin 账号）."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException

from sensehub.api.deps import get_admin_user
from sensehub.db import users as user_store
from sensehub.db import wallet as wallet_store

router = APIRouter(prefix="/admin", tags=["admin"])


class GrantPointsRequest(BaseModel):
    amount: int = Field(gt=0, le=1_000_000)
    note: str = ""


@router.get("/users")
async def admin_list_users(q: str = "", _admin: str = Depends(get_admin_user)):
    items = user_store.search_users(q, limit=100)
    return {"items": items}


@router.post("/users/{user_id}/grant-points")
async def admin_grant_points(
    user_id: str,
    body: GrantPointsRequest,
    admin: str = Depends(get_admin_user),
):
    try:
        return wallet_store.admin_grant_points(admin, user_id, body.amount, body.note)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
