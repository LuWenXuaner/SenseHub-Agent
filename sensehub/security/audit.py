"""审计日志."""

from __future__ import annotations

from sensehub.db.database import get_connection


def log_audit(
    *,
    input_text: str,
    action: str,
    risk_level: str = "L1",
    result: str = "ok",
    trace_id: str = "",
    user_label: str = "local",
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (user_label, input_text, action, risk_level, result, trace_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_label, input_text, action, risk_level, result, trace_id),
        )


def list_audit(limit: int = 100) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
