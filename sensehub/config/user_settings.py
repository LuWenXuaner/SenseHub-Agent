"""用户可覆盖的 API / 模型配置（SQLite，优先于 local.env）."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from sensehub.config.brain_routes import get_brain_presets, get_role_meta
from sensehub.db.database import get_connection
from sensehub.settings import get_settings

_LEGACY_KEYS = (
    "siliconflow_api_key",
    "volcengine_api_key",
    "siliconflow_base_url",
    "volcengine_base_url",
    "planner_model",
    "vision_model",
    "chat_model",
)

# OpenAI 兼容默认端点（可在 models.yaml 用 default_base_url 覆盖）
_DEFAULT_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "deepseek": "https://api.deepseek.com/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "mimo": "https://api.xiaomimimo.com/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "minimax": "https://api.minimax.chat/v1",
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "volcengine": "https://ark.cn-beijing.volces.com/api/v3",
}


def _load_raw() -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM security_settings WHERE key = 'user_api_config'"
        ).fetchone()
    if not row:
        return {}
    data = json.loads(row["value"] or "{}")
    return data if isinstance(data, dict) else {}


def _save_raw(data: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO security_settings (key, value) VALUES ('user_api_config', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (json.dumps(data, ensure_ascii=False),),
        )


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return value[:4] + "…" + value[-4:]


def _provider_catalog() -> dict[str, dict[str, Any]]:
    return get_settings().models_config.get("providers") or {}


def _env_value(name: str) -> str:
    if not name:
        return ""
    return os.getenv(name, "").strip()


def _legacy_credentials(provider: str) -> tuple[str, str]:
    settings = get_settings()
    if provider == "volcengine":
        return settings.volcengine_base_url.rstrip("/"), settings.volcengine_api_key
    if provider == "siliconflow":
        return settings.siliconflow_base_url.rstrip("/"), settings.siliconflow_api_key
    return "", ""


def _user_provider_override(overrides: dict[str, Any], provider: str) -> dict[str, str]:
    bucket = overrides.get("providers")
    if not isinstance(bucket, dict):
        return {}
    row = bucket.get(provider)
    return row if isinstance(row, dict) else {}


def get_provider_credentials(provider: str) -> tuple[str, str]:
    """返回 (base_url, api_key)。支持 models.yaml 中任意 OpenAI 兼容提供商."""
    provider = (provider or "siliconflow").strip()
    overrides = _load_raw()
    catalog = _provider_catalog()
    meta = catalog.get(provider, {}) if isinstance(catalog.get(provider), dict) else {}

    user_row = _user_provider_override(overrides, provider)
    base = str(user_row.get("base_url") or "").strip()
    key = str(user_row.get("api_key") or "").strip()

    if not base or not key:
        legacy_base, legacy_key = _legacy_credentials(provider)
        base = base or legacy_base
        key = key or legacy_key

    if not base:
        base = str(meta.get("default_base_url") or _DEFAULT_BASE_URLS.get(provider) or "").strip()
    if not base:
        base = _env_value(str(meta.get("base_url_env") or ""))
    if not key:
        key = _env_value(str(meta.get("api_key_env") or ""))

    return base.rstrip("/"), key


def _provider_label(provider_id: str, meta: dict[str, Any]) -> str:
    return str(meta.get("label") or provider_id).strip() or provider_id


def _roles_by_provider() -> dict[str, list[str]]:
    roles = get_settings().models_config.get("roles") or {}
    out: dict[str, list[str]] = {}
    for role, cfg in roles.items():
        if not isinstance(cfg, dict):
            continue
        pid = str(cfg.get("provider") or "").strip()
        if not pid:
            continue
        out.setdefault(pid, []).append(str(role))
    return out


def _provider_public_row(provider_id: str, meta: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    user_row = _user_provider_override(overrides, provider_id)
    flat_key = overrides.get(f"{provider_id}_api_key")
    if user_row.get("api_key") or flat_key:
        source = "user"
    else:
        _, key_probe = get_provider_credentials(provider_id)
        source = "env" if key_probe else "none"
    base, key = get_provider_credentials(provider_id)
    configured = bool(base and key)
    return {
        "id": provider_id,
        "label": _provider_label(provider_id, meta),
        "base_url": base,
        "api_key": mask_secret(key),
        "configured": configured,
        "source": source if configured else "none",
        "api_style": str(meta.get("api_style") or "openai"),
        "roles": _roles_by_provider().get(provider_id, []),
        "default_base_url": str(
            meta.get("default_base_url") or _DEFAULT_BASE_URLS.get(provider_id) or ""
        ),
    }


def get_api_config_public() -> dict:
    settings = get_settings()
    overrides = _load_raw()
    cfg = settings.models_config
    roles_cfg = cfg.get("roles", {})
    catalog = _provider_catalog()

    providers_out = [
        _provider_public_row(pid, meta if isinstance(meta, dict) else {}, overrides)
        for pid, meta in catalog.items()
    ]

    user_routes = get_user_role_routes()
    roles_out = []
    for role, row in roles_cfg.items():
        if not isinstance(row, dict):
            continue
        default_provider = str(row.get("provider") or "")
        default_model = str(row.get("model") or "")
        effective_provider, effective_model = resolve_role_binding(role)
        prov = next((p for p in providers_out if p["id"] == effective_provider), None)
        meta = get_role_meta(role)
        roles_out.append(
            {
                "role": role,
                "label_zh": str(meta.get("label_zh") or role),
                "label_en": str(meta.get("label_en") or role),
                "provider": effective_provider,
                "provider_label": prov["label"] if prov else effective_provider,
                "model": effective_model,
                "default_provider": default_provider,
                "default_model": default_model,
                "description": row.get("description", ""),
                "description_zh": str(meta.get("description_zh") or row.get("description") or ""),
                "description_en": str(meta.get("description_en") or row.get("description") or ""),
                "configured": bool(prov and prov["configured"]),
                "user_override": role in user_routes,
            }
        )

    return {
        "providers": providers_out,
        "roles": roles_out,
        "role_routes": user_routes,
        "brain_presets": get_brain_presets(),
        "planner_model": overrides.get("planner_model") or roles_cfg.get("planner", {}).get("model", ""),
        "vision_model": overrides.get("vision_model") or roles_cfg.get("vision", {}).get("model", ""),
        "chat_model": overrides.get("chat_model") or roles_cfg.get("intent", {}).get("model", ""),
        # 兼容旧前端字段
        "siliconflow_api_key": next((p["api_key"] for p in providers_out if p["id"] == "siliconflow"), ""),
        "volcengine_api_key": next((p["api_key"] for p in providers_out if p["id"] == "volcengine"), ""),
        "siliconflow_base_url": next((p["base_url"] for p in providers_out if p["id"] == "siliconflow"), ""),
        "volcengine_base_url": next((p["base_url"] for p in providers_out if p["id"] == "volcengine"), ""),
        "sources": {
            p["id"]: p["source"] for p in providers_out
        },
    }


def update_api_config(payload: dict[str, Any]) -> dict:
    current = _load_raw()
    providers = dict(current.get("providers") or {}) if isinstance(current.get("providers"), dict) else {}

    if isinstance(payload.get("providers"), dict):
        for pid, row in payload["providers"].items():
            if not isinstance(row, dict):
                continue
            entry = dict(providers.get(pid) or {})
            base = str(row.get("base_url") or "").strip()
            key = str(row.get("api_key") or "").strip()
            if base:
                entry["base_url"] = base
            if key and not key.startswith("****") and "…" not in key:
                entry["api_key"] = key
            if entry:
                providers[str(pid)] = entry
        current["providers"] = providers

    for key in _LEGACY_KEYS:
        if key not in payload:
            continue
        val = str(payload.get(key) or "").strip()
        if not val or val.startswith("****") or "…" in val:
            continue
        current[key] = val
        if key.endswith("_api_key"):
            pid = key.replace("_api_key", "")
            row = dict(providers.get(pid) or {})
            row["api_key"] = val
            providers[pid] = row
        elif key.endswith("_base_url"):
            pid = key.replace("_base_url", "")
            row = dict(providers.get(pid) or {})
            row["base_url"] = val
            providers[pid] = row
    current["providers"] = providers

    if isinstance(payload.get("role_routes"), dict):
        routes = dict(current.get("role_routes") or {}) if isinstance(current.get("role_routes"), dict) else {}
        for role, row in payload["role_routes"].items():
            if not isinstance(row, dict):
                continue
            role_key = str(role).strip()
            if not role_key:
                continue
            provider = str(row.get("provider") or "").strip()
            model = str(row.get("model") or "").strip()
            if not provider and not model:
                routes.pop(role_key, None)
                continue
            if provider and model:
                routes[role_key] = {"provider": provider, "model": model}
        if routes:
            current["role_routes"] = routes
        else:
            current.pop("role_routes", None)

    _save_raw(current)
    return get_api_config_public()


def clear_api_overrides() -> dict:
    with get_connection() as conn:
        conn.execute("DELETE FROM security_settings WHERE key = 'user_api_config'")
    return get_api_config_public()


def get_default_save_path() -> str:
    return str(_load_raw().get("default_save_path") or "").strip()


def builtin_default_save_path() -> str:
    """项目根目录下的 result 文件夹（用户未自定义时的默认落盘位置）."""
    from sensehub.settings import get_settings

    root = Path(get_settings().sensehub_root)
    try:
        p = (root / "result").resolve()
        p.mkdir(parents=True, exist_ok=True)
        return str(p)
    except OSError:
        return ""


def ensure_default_save_path_ready() -> str:
    """启动时确保默认交付目录存在、已授权；未自定义时写入 result 并持久化."""
    from sensehub.security.sandbox import add_runtime_grant

    custom = get_default_save_path()
    if custom:
        try:
            add_runtime_grant(custom)
        except OSError:
            pass
        return custom
    builtin = builtin_default_save_path()
    if not builtin:
        return ""
    try:
        add_runtime_grant(builtin)
    except OSError:
        pass
    return set_default_save_path(builtin)


def get_effective_default_save_path() -> str:
    custom = get_default_save_path()
    if custom:
        return custom
    return builtin_default_save_path()


def set_default_save_path(path_str: str) -> str:
    """设置 Console 默认保存路径，并加入沙箱可写授权."""
    from sensehub.security.sandbox import add_runtime_grant

    path_str = str(path_str or "").strip()
    current = _load_raw()
    if not path_str:
        current.pop("default_save_path", None)
        _save_raw(current)
        return ""
    p = Path(path_str).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    add_runtime_grant(str(p))
    current["default_save_path"] = str(p)
    _save_raw(current)
    return str(p)


def get_console_settings_public() -> dict[str, str]:
    from sensehub.security.sandbox import workspace_dir

    save = get_effective_default_save_path()
    user_set = bool(get_default_save_path())
    return {
        "default_save_path": save,
        "default_save_path_user_set": str(user_set).lower(),
        "workspace": str(workspace_dir()),
    }


def get_role_model(role: str) -> str | None:
    overrides = _load_raw()
    mapping = {
        "planner": "planner_model",
        "vision": "vision_model",
        "intent": "chat_model",
        "coder": "chat_model",
        "safety": "chat_model",
    }
    key = mapping.get(role)
    if key and overrides.get(key):
        return str(overrides[key])
    return None


def _default_role_binding(role: str) -> tuple[str, str]:
    roles_cfg = get_settings().models_config.get("roles") or {}
    row = roles_cfg.get(role)
    if not isinstance(row, dict):
        row = roles_cfg.get("planner", {})
    if not isinstance(row, dict):
        row = {}
    provider = str(row.get("provider") or "siliconflow").strip()
    model = str(row.get("model") or "Qwen/Qwen3-8B").strip()
    return provider, model


def resolve_role_binding(role: str) -> tuple[str, str]:
    """返回生效的 (provider, model)。用户 role_routes 优先，其次旧版单模型覆盖."""
    default_provider, default_model = _default_role_binding(role)
    overrides = _load_raw()

    role_routes = overrides.get("role_routes")
    if isinstance(role_routes, dict) and role in role_routes:
        row = role_routes[role]
        if isinstance(row, dict):
            provider = str(row.get("provider") or "").strip()
            model = str(row.get("model") or "").strip()
            if provider and model:
                return provider, model

    legacy_model = get_role_model(role)
    if legacy_model:
        return default_provider, legacy_model

    return default_provider, default_model


def get_user_role_routes() -> dict[str, dict[str, str]]:
    overrides = _load_raw()
    raw = overrides.get("role_routes")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for role, row in raw.items():
        if not isinstance(row, dict):
            continue
        provider = str(row.get("provider") or "").strip()
        model = str(row.get("model") or "").strip()
        if provider and model:
            out[str(role)] = {"provider": provider, "model": model}
    return out
