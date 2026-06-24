"""档位与用量."""

from __future__ import annotations

from datetime import date

from sensehub.db.database import get_connection
from sensehub.models.schemas import LicenseInfo, TierName
from sensehub.settings import get_settings

TIER_LIMITS = {
    "lite": {"text_commands": 20},
    "pro": {"text_commands": None},
    "max": {"text_commands": None},
}

TIER_FEATURES = {
    "lite": {
        "voice_stream": False,
        "gesture_rules": False,
        "virtual_screen": False,
        "lan_access": False,
        "tts_feedback": False,
        "multi_agent": False,
        "secure_tunnel": False,
        "camera_preview": True,
        "person_detection": True,
        "rules_limit": 3,
        "vlm_gui_agent": True,
    },
    "pro": {
        "voice_stream": True,
        "gesture_rules": True,
        "virtual_screen": False,
        "lan_access": True,
        "tts_feedback": True,
        "multi_agent": False,
        "secure_tunnel": False,
        "camera_preview": True,
        "person_detection": True,
        "rules_limit": 50,
        "vlm_gui_agent": True,
    },
    "max": {
        "voice_stream": True,
        "gesture_rules": True,
        "virtual_screen": True,
        "lan_access": True,
        "tts_feedback": True,
        "multi_agent": True,
        "secure_tunnel": True,
        "camera_preview": True,
        "person_detection": True,
        "rules_limit": None,
        "vlm_gui_agent": True,
    },
}


def feature_enabled(name: str, username: str | None = None) -> bool:
    feats = TIER_FEATURES.get(get_tier(username), TIER_FEATURES["lite"])
    return bool(feats.get(name, False))


def get_tier(username: str | None = None) -> TierName:
    if username:
        from sensehub.db import wallet as wallet_store

        tier = wallet_store.get_user_tier(username)
        if tier in ("lite", "pro", "max"):
            return tier  # type: ignore
    tier = get_settings().license_tier.lower()
    if tier not in ("lite", "pro", "max"):
        return "lite"
    return tier  # type: ignore


def _today() -> str:
    return date.today().isoformat()


def get_text_usage() -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT count FROM usage_daily WHERE day = ? AND metric = ?",
            (_today(), "text_commands"),
        ).fetchone()
    return int(row["count"]) if row else 0


def increment_text_usage() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO usage_daily (day, metric, count) VALUES (?, ?, 1)
            ON CONFLICT(day, metric) DO UPDATE SET count = count + 1
            """,
            (_today(), "text_commands"),
        )


def check_text_quota() -> tuple[bool, str]:
    tier = get_tier()
    limit = TIER_LIMITS[tier]["text_commands"]
    if limit is None:
        return True, "ok"
    used = get_text_usage()
    if used >= limit:
        return False, f"Lite 档位今日文本指令已达上限 ({limit} 次)"
    return True, "ok"


def reset_text_usage_today() -> None:
    """冒烟测试前重置当日文本用量."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM usage_daily WHERE day = ? AND metric = ?",
            (_today(), "text_commands"),
        )


def get_license_info(username: str | None = None) -> LicenseInfo:
    tier = get_tier(username)
    limit = TIER_LIMITS[tier]["text_commands"]
    expires_at: str | None = None
    sub_active = False
    if username:
        from sensehub.db import wallet as wallet_store

        sub = wallet_store.get_subscription_status(username)
        expires_at = sub.get("tier_expires_at")
        sub_active = bool(sub.get("active"))
    used = get_text_usage()
    return LicenseInfo(
        tier=tier,
        text_commands_used=used,
        text_commands_limit=limit,
        features=TIER_FEATURES[tier],
        tier_expires_at=expires_at,
        subscription_active=sub_active,
        text_commands_unlimited=limit is None,
    )


def get_rules_limit() -> int | None:
    return TIER_FEATURES.get(get_tier(), {}).get("rules_limit")
