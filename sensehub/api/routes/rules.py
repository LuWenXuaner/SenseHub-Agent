"""规则 CRUD API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sensehub.api.deps import get_current_user
from sensehub.licensing.tier import get_rules_limit
from sensehub.models.perception_schemas import Rule, RuleCreate
from sensehub.rules import store as rule_store

router = APIRouter(tags=["rules"])


@router.get("/rules", response_model=list[Rule])
async def list_rules(_: str = Depends(get_current_user)):
    return rule_store.list_rules()


@router.post("/rules", response_model=Rule)
async def create_rule(body: RuleCreate, _: str = Depends(get_current_user)):
    limit = get_rules_limit()
    if limit is not None and rule_store.count_rules() >= limit:
        raise HTTPException(status_code=403, detail=f"当前档位最多 {limit} 条规则")
    return rule_store.create_rule(body)


@router.put("/rules/{rule_id}", response_model=Rule)
async def update_rule(rule_id: str, body: RuleCreate, _: str = Depends(get_current_user)):
    rule = rule_store.update_rule(rule_id, body)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, _: str = Depends(get_current_user)):
    if not rule_store.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"status": "ok"}
