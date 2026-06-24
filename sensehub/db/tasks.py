"""任务持久化."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sensehub.db.database import get_connection
from sensehub.models.schemas import PlanStep, StepResult, TaskResponse, TaskStatus


def create_task(intent_text: str, trace_id: str | None = None) -> str:
    task_id = str(uuid.uuid4())
    trace = trace_id or str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, status, intent_text, trace_id) VALUES (?, ?, ?, ?)",
            (task_id, "pending", intent_text, trace),
        )
    return task_id


def update_task(
    task_id: str,
    *,
    status: TaskStatus | None = None,
    summary: str | None = None,
    plan_steps: list[PlanStep] | None = None,
    current_step: int | None = None,
    step_results: list[StepResult] | None = None,
    error: str | None = None,
    trace_id: str | None = None,
) -> None:
    fields: list[str] = ["updated_at = datetime('now')"]
    values: list[object] = []

    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if summary is not None:
        fields.append("summary = ?")
        values.append(summary)
    if plan_steps is not None:
        fields.append("plan_json = ?")
        values.append(json.dumps([s.model_dump() for s in plan_steps], ensure_ascii=False))
    if current_step is not None:
        fields.append("current_step = ?")
        values.append(current_step)
    if step_results is not None:
        fields.append("results_json = ?")
        values.append(json.dumps([r.model_dump() for r in step_results], ensure_ascii=False))
    if error is not None:
        fields.append("error = ?")
        values.append(error)
    if trace_id is not None:
        fields.append("trace_id = ?")
        values.append(trace_id)

    values.append(task_id)
    sql = f"UPDATE tasks SET {', '.join(fields)} WHERE task_id = ?"
    with get_connection() as conn:
        conn.execute(sql, values)


def get_task(task_id: str) -> TaskResponse | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    if not row:
        return None
    plan = json.loads(row["plan_json"] or "[]")
    results = json.loads(row["results_json"] or "[]")
    steps = [PlanStep(**s) for s in plan]
    needs_confirm = row["status"] == "wait_confirm"
    return TaskResponse(
        task_id=row["task_id"],
        status=row["status"],
        intent_text=row["intent_text"],
        summary=row["summary"] or "",
        plan_steps=steps,
        current_step=row["current_step"] or 0,
        step_results=[StepResult(**r) for r in results],
        error=row["error"],
        trace_id=row["trace_id"] or "",
        needs_confirm=needs_confirm,
    )


def list_tasks(limit: int = 50) -> list[TaskResponse]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT task_id FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [t for row in rows if (t := get_task(row["task_id"]))]
