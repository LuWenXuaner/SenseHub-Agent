"""邮箱验证码（SMTP 或开发模式）."""

from __future__ import annotations

import random
import smtplib
import string
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from sensehub.db.database import get_connection
from sensehub.settings import get_settings

_CODE_TTL_MINUTES = 10


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def send_verification_code(email: str, *, purpose: str = "register") -> dict:
    from sensehub.db import users as user_store

    email = email.strip().lower()
    if "@" not in email or len(email) < 5:
        raise ValueError("邮箱格式不正确")
    if purpose == "register" and user_store.get_user_by_email(email):
        raise ValueError("该邮箱已注册")
    if purpose == "reset" and not user_store.get_user_by_email(email):
        raise ValueError("该邮箱未注册")

    code = _generate_code()
    expires = datetime.now(timezone.utc) + timedelta(minutes=_CODE_TTL_MINUTES)
    with get_connection() as conn:
        conn.execute("DELETE FROM email_verification_codes WHERE email = ? AND purpose = ?", (email, purpose))
        conn.execute(
            """
            INSERT INTO email_verification_codes (email, code, purpose, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (email, code, purpose, expires.isoformat()),
        )

    settings = get_settings()
    sent = False
    if settings.smtp_host and settings.smtp_from:
        try:
            msg = MIMEText(f"您的灵枢 Agent 验证码为：{code}，{_CODE_TTL_MINUTES} 分钟内有效。")
            msg["Subject"] = "灵枢 Agent 验证码"
            msg["From"] = settings.smtp_from
            msg["To"] = email
            if settings.smtp_port == 465:
                with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                    if settings.smtp_user:
                        smtp.login(settings.smtp_user, settings.smtp_password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                    if settings.smtp_user:
                        smtp.starttls()
                        smtp.login(settings.smtp_user, settings.smtp_password)
                    smtp.send_message(msg)
            sent = True
        except Exception:
            sent = False

    result = {"email": email, "sent": sent, "expires_in": _CODE_TTL_MINUTES * 60}
    if not sent and settings.email_dev_expose_code:
        result["dev_code"] = code
    elif not sent:
        raise RuntimeError("邮件服务未配置，请在 config/local.env 设置 SMTP 或开启 EMAIL_DEV_EXPOSE_CODE")
    return result


def verify_code(email: str, code: str, *, purpose: str = "register") -> bool:
    email = email.strip().lower()
    code = code.strip()
    if not code:
        return False
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT code, expires_at FROM email_verification_codes
            WHERE email = ? AND purpose = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (email, purpose),
        ).fetchone()
        if not row or row["code"] != code:
            return False
        if row["expires_at"] < now:
            return False
        conn.execute("DELETE FROM email_verification_codes WHERE email = ? AND purpose = ?", (email, purpose))
    return True
