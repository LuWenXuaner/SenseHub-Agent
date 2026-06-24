"""Console Harness 策略加载."""

from __future__ import annotations

from typing import Any

import yaml

from sensehub.settings import CONFIG_DIR

_PATH = CONFIG_DIR / "console_harness.yaml"
_cache: tuple[float, dict[str, Any]] | None = None


def _load() -> dict[str, Any]:
    global _cache
    mtime = _PATH.stat().st_mtime if _PATH.exists() else 0.0
    if _cache and _cache[0] == mtime:
        return _cache[1]
    if not _PATH.exists():
        data: dict[str, Any] = {}
    else:
        raw = yaml.safe_load(_PATH.read_text(encoding="utf-8")) or {}
        data = raw if isinstance(raw, dict) else {}
    _cache = (mtime, data)
    return data


def harness_policy_block() -> str:
  policies = _load().get("policies")
  if not isinstance(policies, dict):
    return ""
  parts = [str(v).strip() for v in policies.values() if str(v).strip()]
  if not parts:
    return ""
  return "\n### Console Harness 规程\n" + "\n\n".join(parts)
