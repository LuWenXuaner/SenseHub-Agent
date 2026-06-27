"""规划模板持久化."""

from __future__ import annotations

import uuid

from sensehub.db.database import get_connection


def upsert(
    *,
    intent_fingerprint: str,
    tool_signature: str,
    intent_snapshot: str,
    plan_json: str,
    summary: str,
) -> None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT template_id, fail_count FROM plan_templates WHERE intent_fingerprint = ?",
            (intent_fingerprint,),
        ).fetchone()
        if row:
            if int(row["fail_count"] or 0) >= 3:
                return
            conn.execute(
                """
                UPDATE plan_templates
                SET tool_signature = ?,
                    intent_snapshot = ?,
                    plan_json = ?,
                    summary = ?,
                    success_count = success_count + 1,
                    last_used_at = datetime('now')
                WHERE template_id = ?
                """,
                (tool_signature, intent_snapshot, plan_json, summary, row["template_id"]),
            )
            return
        conn.execute(
            """
            INSERT INTO plan_templates (
                template_id, intent_fingerprint, tool_signature,
                intent_snapshot, plan_json, summary, success_count, fail_count
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 0)
            """,
            (str(uuid.uuid4()), intent_fingerprint, tool_signature, intent_snapshot, plan_json, summary),
        )


def get_by_fingerprint(intent_fingerprint: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM plan_templates
            WHERE intent_fingerprint = ? AND fail_count < 3 AND success_count >= 1
            ORDER BY success_count DESC LIMIT 1
            """,
            (intent_fingerprint,),
        ).fetchone()
    return dict(row) if row else None


def get_by_tool_signature(tool_signature: str) -> dict | None:
    if not tool_signature:
        return None
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM plan_templates
            WHERE tool_signature = ? AND fail_count < 3 AND success_count >= 2
            ORDER BY success_count DESC LIMIT 1
            """,
            (tool_signature,),
        ).fetchone()
    return dict(row) if row else None


def touch(template_id: str, *, success: bool) -> None:
    field = "success_count" if success else "fail_count"
    with get_connection() as conn:
        conn.execute(
            f"""
            UPDATE plan_templates
            SET {field} = {field} + 1, last_used_at = datetime('now')
            WHERE template_id = ?
            """,
            (template_id,),
        )
