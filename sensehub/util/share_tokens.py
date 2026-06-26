"""成就分享等公开链接令牌."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from sensehub.security.auth import ALGORITHM
from sensehub.settings import get_settings

_SHARE_TYP = "achievement_share"


def create_achievement_share_token(*, user_id: str, achievement_id: str, days: int = 90) -> str:
    uid = str(user_id or "").strip()
    aid = str(achievement_id or "").strip()
    if not uid or not aid:
        raise ValueError("分享令牌参数无效")
    expire = datetime.now(timezone.utc) + timedelta(days=max(1, min(days, 365)))
    payload = {"typ": _SHARE_TYP, "uid": uid, "aid": aid, "exp": expire}
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=ALGORITHM)


def decode_achievement_share_token(token: str) -> tuple[str, str] | None:
    text = (token or "").strip()
    if not text:
        return None
    try:
        payload = jwt.decode(text, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("typ") != _SHARE_TYP:
        return None
    uid = str(payload.get("uid") or "").strip()
    aid = str(payload.get("aid") or "").strip()
    if not uid or not aid:
        return None
    return uid, aid
