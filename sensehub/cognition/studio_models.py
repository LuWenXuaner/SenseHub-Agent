"""灵枢 Chat 模型目录：前端 model_id → provider + API model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from sensehub.settings import CONFIG_DIR, get_settings

CONFIG_PATH = CONFIG_DIR / "studio_models.yaml"

_catalog_cache: tuple[float, dict[str, Any]] | None = None


@dataclass(frozen=True)
class StudioModelRoute:
    model_id: str
    provider: str
    model: str
    label: str = ""
    available: bool = True
    reason: str = ""


class StudioModelError(ValueError):
    """用户可读的模型路由错误."""


def _load_catalog() -> dict[str, Any]:
    global _catalog_cache
    mtime = CONFIG_PATH.stat().st_mtime if CONFIG_PATH.exists() else 0.0
    if _catalog_cache and _catalog_cache[0] == mtime:
        return _catalog_cache[1]

    if not CONFIG_PATH.exists():
        data: dict[str, Any] = {}
    else:
        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        models = raw.get("models")
        data = models if isinstance(models, dict) else {}

    _catalog_cache = (mtime, data)
    return data


def _provider_label(provider_id: str) -> str:
    catalog = get_settings().models_config.get("providers") or {}
    meta = catalog.get(provider_id)
    if isinstance(meta, dict) and meta.get("label"):
        return str(meta["label"])
    return provider_id


def resolve_studio_model(model_id: str) -> StudioModelRoute | None:
    """解析 Chat 所选 model_id；空字符串返回 None（走 intent 默认路由）."""
    mid = (model_id or "").strip()
    if not mid:
        return None

    row = _load_catalog().get(mid)
    if not isinstance(row, dict):
        raise StudioModelError(
            f"未找到模型「{mid}」的后端映射，请重启后端或检查 config/studio_models.yaml"
        )

    label = str(row.get("label") or mid).strip()
    available = row.get("available", True)
    if available is False:
        reason = str(row.get("reason") or "该模型暂不可用，请换一个已支持的模型")
        return StudioModelRoute(model_id=mid, provider="", model="", label=label, available=False, reason=reason)

    provider = str(row.get("provider") or "").strip()
    model = str(row.get("model") or "").strip()
    if not provider or not model:
        return StudioModelRoute(
            model_id=mid,
            provider="",
            model="",
            label=label,
            available=False,
            reason="该模型映射未配置完整，请联系管理员",
        )

    return StudioModelRoute(
        model_id=mid,
        provider=provider,
        model=model,
        label=label,
        available=True,
    )


def provider_display_label(provider_id: str) -> str:
    return _provider_label(provider_id)


def provider_key_hint(provider_id: str) -> str:
    label = _provider_label(provider_id)
    return f"请先在控制台「API Keys」中配置 {label} 的 API Key"
