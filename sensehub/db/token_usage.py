"""LLM Token 用量持久化与查询."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sensehub.db.database import get_connection


def _day_key(dt: datetime | None = None) -> str:
    t = dt or datetime.now(timezone.utc)
    return t.strftime("%Y-%m-%d")


def record_llm_usage(
    *,
    user_id: str,
    role: str,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    uid = str(user_id or "").strip()
    if not uid or uid == "local":
        return
    day = _day_key()
    prompt_tokens = max(0, int(prompt_tokens))
    completion_tokens = max(0, int(completion_tokens))
    total = prompt_tokens + completion_tokens
    if total <= 0:
        return
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO llm_token_usage (
                user_id, day, role, provider, model,
                prompt_tokens, completion_tokens, total_tokens, request_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(user_id, day, role, provider, model) DO UPDATE SET
                prompt_tokens = prompt_tokens + excluded.prompt_tokens,
                completion_tokens = completion_tokens + excluded.completion_tokens,
                total_tokens = total_tokens + excluded.total_tokens,
                request_count = request_count + 1
            """,
            (uid, day, role, provider, model, prompt_tokens, completion_tokens, total),
        )


def _username_to_user_id(username: str) -> str:
    from sensehub.db.wallet import _username_to_user_id as _map

    return _map(username)


def _fill_daily_series(rows: list[dict[str, Any]], *, days: int) -> list[dict[str, Any]]:
    """补全连续日历日，无记录日期填 0."""
    span = max(1, min(int(days), 366))
    by_day = {str(r.get("day")): r for r in rows if r.get("day")}
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=span - 1)
    out: list[dict[str, Any]] = []
    cur = start
    while cur <= end:
        key = cur.isoformat()
        if key in by_day:
            row = by_day[key]
            out.append(
                {
                    "day": key,
                    "total_tokens": int(row.get("total_tokens") or 0),
                    "request_count": int(row.get("request_count") or 0),
                }
            )
        else:
            out.append({"day": key, "total_tokens": 0, "request_count": 0})
        cur += timedelta(days=1)
    return out


def token_usage_summary(username: str, *, days: int = 30) -> dict[str, Any]:
    span = max(7, min(int(days), 366))
    user_id = _username_to_user_id(username)
    if not user_id:
        return {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "request_count": 0,
            "by_model": [],
            "daily": [],
        }
    with get_connection() as conn:
        total_row = conn.execute(
            """
            SELECT
                COALESCE(SUM(total_tokens), 0) AS total_tokens,
                COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                COALESCE(SUM(request_count), 0) AS request_count
            FROM llm_token_usage
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        by_model = conn.execute(
            """
            SELECT role, provider, model,
                   SUM(total_tokens) AS total_tokens,
                   SUM(request_count) AS request_count
            FROM llm_token_usage
            WHERE user_id = ?
            GROUP BY role, provider, model
            ORDER BY total_tokens DESC
            LIMIT 40
            """,
            (user_id,),
        ).fetchall()
        daily = conn.execute(
            """
            SELECT day,
                   SUM(total_tokens) AS total_tokens,
                   SUM(request_count) AS request_count
            FROM llm_token_usage
            WHERE user_id = ?
            GROUP BY day
            ORDER BY day DESC
            LIMIT ?
            """,
            (user_id, span),
        ).fetchall()
    filled = _fill_daily_series([dict(r) for r in daily], days=span)
    return {
        "total_tokens": int(total_row["total_tokens"]) if total_row else 0,
        "prompt_tokens": int(total_row["prompt_tokens"]) if total_row else 0,
        "completion_tokens": int(total_row["completion_tokens"]) if total_row else 0,
        "request_count": int(total_row["request_count"]) if total_row else 0,
        "by_model": [dict(r) for r in by_model],
        "daily": filled,
        "range_days": span,
    }
