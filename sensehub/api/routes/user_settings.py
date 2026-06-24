"""用户 API 配置."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends

from sensehub.api.deps import get_current_user
from sensehub.api.native_dialogs import pick_folder_dialog
from sensehub.config.user_settings import (
    clear_api_overrides,
    get_api_config_public,
    get_console_settings_public,
    set_default_save_path,
    update_api_config,
)

router = APIRouter(tags=["user-settings"])


class ProviderCredentialsUpdate(BaseModel):
    base_url: str = ""
    api_key: str = ""


class RoleRouteUpdate(BaseModel):
    provider: str = ""
    model: str = ""


class ApiConfigUpdate(BaseModel):
    siliconflow_api_key: str = ""
    volcengine_api_key: str = ""
    siliconflow_base_url: str = ""
    volcengine_base_url: str = ""
    planner_model: str = ""
    vision_model: str = ""
    chat_model: str = ""
    providers: dict[str, ProviderCredentialsUpdate] = Field(default_factory=dict)
    role_routes: dict[str, RoleRouteUpdate] = Field(default_factory=dict)


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
    if body.role_routes:
        payload["role_routes"] = {
            k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in body.role_routes.items()
        }
    return update_api_config(payload)


@router.delete("/settings/api")
async def reset_api_config(_: str = Depends(get_current_user)):
    return clear_api_overrides()


class ConsoleSettingsUpdate(BaseModel):
    default_save_path: str = ""


@router.get("/settings/console")
async def read_console_settings(_: str = Depends(get_current_user)):
    return get_console_settings_public()


@router.put("/settings/console")
async def write_console_settings(body: ConsoleSettingsUpdate, _: str = Depends(get_current_user)):
    path = set_default_save_path(body.default_save_path)
    return get_console_settings_public() | {"default_save_path": path}


@router.post("/settings/console/pick-folder")
async def pick_console_save_folder(_: str = Depends(get_current_user)):
    """打开本机文件夹选择对话框并保存为默认保存路径."""
    # tkinter 须在主线程运行；asyncio.to_thread 在 Windows 上易触发 Tcl 线程错误
    try:
        chosen = pick_folder_dialog("选择灵枢 Console 默认保存文件夹")
    except Exception as exc:
        return {"cancelled": True, "error": str(exc), **get_console_settings_public()}
    if not chosen:
        return {"cancelled": True, **get_console_settings_public()}
    try:
        saved = set_default_save_path(chosen)
    except OSError as exc:
        return {"cancelled": True, "error": f"无法写入该路径：{exc}", **get_console_settings_public()}
    return {"cancelled": False, "default_save_path": saved, **get_console_settings_public()}
