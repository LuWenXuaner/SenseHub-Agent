"""用户 API 配置."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends

from sensehub.api.deps import get_current_user
from sensehub.config.user_settings import clear_api_overrides, get_api_config_public, update_api_config

router = APIRouter(tags=["user-settings"])


class ProviderCredentialsUpdate(BaseModel):
    base_url: str = ""
    api_key: str = ""


class ApiConfigUpdate(BaseModel):
    siliconflow_api_key: str = ""
    volcengine_api_key: str = ""
    siliconflow_base_url: str = ""
    volcengine_base_url: str = ""
    planner_model: str = ""
    vision_model: str = ""
    chat_model: str = ""
    providers: dict[str, ProviderCredentialsUpdate] = Field(default_factory=dict)


@router.get("/settings/api")
async def read_api_config(_: str = Depends(get_current_user)):
    return get_api_config_public()


@router.put("/settings/api")
async def write_api_config(body: ApiConfigUpdate, _: str = Depends(get_current_user)):
    payload: dict[str, Any] = body.model_dump()
    if body.providers:
        payload["providers"] = {
            k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in body.providers.items()
        }
    return update_api_config(payload)


@router.delete("/settings/api")
async def reset_api_config(_: str = Depends(get_current_user)):
    return clear_api_overrides()
