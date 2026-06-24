"""感知事件记录."""

from __future__ import annotations

import json

from sensehub.db.database import get_connection
from sensehub.models.perception_schemas import PerceptionEvent


def log_event(
    *,
    event_type: str,
    source: str,
    message: str = "",
    rule_id: str | None = None,
    payload: dict | None = None,
) -> PerceptionEvent:
    payload_json = json.dumps(payload or {}, ensure_ascii=False)
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO perception_events (event_type, source, rule_id, message, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_type, source, rule_id, message, payload_json),
        )
        row = conn.execute(
            "SELECT * FROM perception_events WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return PerceptionEvent(
        id=row["id"],
        timestamp=row["timestamp"],
        event_type=row["event_type"],
        source=row["source"],
        rule_id=row["rule_id"],
        message=row["message"] or "",
        payload=json.loads(row["payload_json"] or "{}"),
    )


def list_events(limit: int = 50) -> list[PerceptionEvent]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM perception_events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    result = []
    for row in rows:
        result.append(
            PerceptionEvent(
                id=row["id"],
                timestamp=row["timestamp"],
                event_type=row["event_type"],
                source=row["source"],
                rule_id=row["rule_id"],
                message=row["message"] or "",
                payload=json.loads(row["payload_json"] or "{}"),
            )
        )
    return result
