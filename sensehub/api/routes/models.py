"""模型配置只读 API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from sensehub.api.deps import get_current_user
from sensehub.perception.device import inference_device_label
from sensehub.settings import get_settings

router = APIRouter(tags=["models"])


@router.get("/models/config")
async def read_models_config(_: str = Depends(get_current_user)):
    settings = get_settings()
    cfg = settings.models_config
    roles = cfg.get("roles", {})
    paths = settings.paths.get("models", {})
    return {
        "roles": roles,
        "defaults": cfg.get("defaults", {}),
        "providers": {
            k: {"base_url_env": v.get("base_url_env"), "api_style": v.get("api_style")}
            for k, v in (cfg.get("providers") or {}).items()
            if isinstance(v, dict)
        },
        "chat": roles.get("intent", {}),
        "vision": roles.get("vision", {}),
        "planner": roles.get("planner", {}),
        "paths": {
            "yolo": paths.get("yolo_weights", ""),
            "yolo_pose": paths.get("yolo_pose_weights", ""),
            "whisper": paths.get("whisper_model", ""),
            "funasr": paths.get("funasr_model", ""),
            "silero_vad": paths.get("silero_vad", ""),
        },
        "inference_device": inference_device_label(),
        "use_cuda": settings.use_cuda,
    }
