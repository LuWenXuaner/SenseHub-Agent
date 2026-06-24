"""Console 各脑角色模型目录（预设与角色元数据）."""

from __future__ import annotations

from typing import Any

import yaml

from sensehub.settings import CONFIG_DIR

CATALOG_PATH = CONFIG_DIR / "console_brain_catalog.yaml"

_catalog_cache: tuple[float, dict[str, Any]] | None = None


def _load_catalog() -> dict[str, Any]:
    global _catalog_cache
    mtime = CATALOG_PATH.stat().st_mtime if CATALOG_PATH.exists() else 0.0
    if _catalog_cache and _catalog_cache[0] == mtime:
        return _catalog_cache[1]

    if not CATALOG_PATH.exists():
        data: dict[str, Any] = {}
    else:
        raw = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")) or {}
        data = raw if isinstance(raw, dict) else {}

    _catalog_cache = (mtime, data)
    return data


def get_brain_presets() -> list[dict[str, str]]:
    rows = _load_catalog().get("presets")
    if not isinstance(rows, list):
        return []
    out: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("provider") or "").strip()
        model = str(row.get("model") or "").strip()
        if not pid or not model:
            continue
        out.append(
            {
                "id": str(row.get("id") or f"{pid}:{model}"),
                "label": str(row.get("label") or model),
                "provider": pid,
                "model": model,
            }
        )
    return out


def get_role_meta(role: str) -> dict[str, str]:
    roles = _load_catalog().get("roles")
    if not isinstance(roles, dict):
        return {}
    row = roles.get(role)
    return row if isinstance(row, dict) else {}
