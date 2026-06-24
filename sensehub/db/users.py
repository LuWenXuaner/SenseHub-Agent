"""本地用户账号."""

from __future__ import annotations

import re
import uuid

from sensehub.db.database import get_connection
from sensehub.security.auth import hash_password, verify_user_password


def count_users() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
    return int(row["c"]) if row else 0


def needs_setup() -> bool:
    return count_users() == 0


def get_user(username: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, display_name, email, created_at FROM users WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, display_name, email, created_at FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    email = email.strip().lower()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, display_name, email, created_at FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    return dict(row) if row else None


def _username_from_email(email: str) -> str:
    local = email.split("@", 1)[0]
    base = re.sub(r"[^a-z0-9_]", "_", local.lower())[:16] or "user"
    username = base
    i = 1
    while get_user(username):
        username = f"{base}{i}"
        i += 1
    return username


def create_user(
    username: str,
    password_plain: str | None = None,
    *,
    password_hash: str | None = None,
    display_name: str = "",
    email: str | None = None,
) -> dict:
    username = username.strip().lower()
    if len(username) < 3:
        raise ValueError("用户名至少 3 个字符")
    if get_user(username):
        raise ValueError("用户名已存在")
    if email:
        email = email.strip().lower()
        if get_user_by_email(email):
            raise ValueError("该邮箱已注册")
    if password_hash is None:
        if not password_plain or len(password_plain) < 6:
            raise ValueError("密码至少 6 个字符")
        password_hash = hash_password(password_plain)
    user_id = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, username, password_hash, display_name, email)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, username, password_hash, display_name or username, email),
        )
    user = get_user(username)
    assert user
    return user


def create_user_with_email(email: str, password: str, *, username: str = "", display_name: str = "") -> dict:
    email = email.strip().lower()
    if get_user_by_email(email):
        raise ValueError("该邮箱已注册")
    uname = username.strip().lower() if username else _username_from_email(email)
    return create_user(uname, password, display_name=display_name or uname, email=email)


def authenticate(username: str, password: str) -> dict | None:
    username = username.strip().lower()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, password_hash, display_name, email, created_at FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if not row:
        return None
    if not verify_user_password(password, row["password_hash"]):
        return None
    return _row_user(row)


def authenticate_by_email(email: str, password: str) -> dict | None:
    email = email.strip().lower()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, password_hash, display_name, email, created_at FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    if not row:
        return None
    if not verify_user_password(password, row["password_hash"]):
        return None
    return _row_user(row)


def _row_user(row) -> dict:
    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "email": row["email"],
        "created_at": row["created_at"],
    }


def change_password(username: str, old_password: str, new_password: str) -> None:
    user = authenticate(username, old_password)
    if not user:
        raise ValueError("当前密码错误")
    pwd_hash = hash_password(new_password)
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (pwd_hash, username.strip().lower()),
        )


def reset_password_by_email(email: str, new_password: str) -> None:
    email = email.strip().lower()
    if len(new_password) < 6:
        raise ValueError("密码至少 6 个字符")
    user = get_user_by_email(email)
    if not user:
        raise ValueError("该邮箱未注册")
    pwd_hash = hash_password(new_password)
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (pwd_hash, email),
        )


def search_users(query: str = "", *, limit: int = 50) -> list[dict]:
    """管理员搜索用户（用户名、邮箱、灵枢 ID、用户 ID）."""
    q = query.strip()
    with get_connection() as conn:
        if q:
            like = f"%{q}%"
            rows = conn.execute(
                """
                SELECT u.user_id, u.username, u.display_name, u.email, u.created_at,
                       w.public_id, w.points_balance, w.tier, w.tier_expires_at, w.invite_code
                FROM users u
                LEFT JOIN user_wallets w ON w.user_id = u.user_id
                WHERE lower(u.username) LIKE lower(?)
                   OR lower(COALESCE(u.email, '')) LIKE lower(?)
                   OR COALESCE(w.public_id, '') LIKE ?
                   OR u.user_id LIKE ?
                ORDER BY u.created_at DESC
                LIMIT ?
                """,
                (like, like, like, like, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT u.user_id, u.username, u.display_name, u.email, u.created_at,
                       w.public_id, w.points_balance, w.tier, w.tier_expires_at, w.invite_code
                FROM users u
                LEFT JOIN user_wallets w ON w.user_id = u.user_id
                ORDER BY u.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]
