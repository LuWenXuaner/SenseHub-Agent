"""认证与 JWT."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from sensehub.settings import get_settings

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    digest = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return digest.decode("utf-8")


def verify_user_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def verify_password(plain: str) -> bool:
    """兼容旧版：仅主密码（无用户表时）."""
    settings = get_settings()
    return plain == settings.admin_password


def create_access_token(subject: str = "admin", hours: int = 24) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=hours)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
