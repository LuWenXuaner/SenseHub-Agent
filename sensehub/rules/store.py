"""规则持久化."""

from __future__ import annotations

import json
import uuid

from sensehub.db.database import get_connection
from sensehub.models.perception_schemas import Rule, RuleCreate, RuleAction, RuleTrigger

_DEFAULT_RULES = [
    {
        "name": "人员出现提醒",
        "enabled": True,
        "tier_min": "lite",
        "trigger": {
            "type": "vision",
            "event": "person_detected",
            "confidence_min": 0.6,
        },
        "action": {"type": "notify", "message": "检测到人员进入画面"},
    },
    {
        "name": "挥手打招呼提醒",
        "enabled": False,
        "tier_min": "lite",
        "trigger": {"type": "gesture", "event": "wave", "confidence_min": 0.55},
        "action": {"type": "notify", "message": "检测到挥手，用户可能在打招呼"},
    },
    {
        "name": "点头确认待确认任务",
        "enabled": False,
        "tier_min": "pro",
        "trigger": {"type": "gesture", "event": "nod", "confidence_min": 0.55},
        "action": {"type": "confirm_pending", "message": "检测到点头，已代为确认待确认任务"},
    },
    {
        "name": "摇头取消待确认任务",
        "enabled": False,
        "tier_min": "pro",
        "trigger": {"type": "gesture", "event": "shake", "confidence_min": 0.55},
        "action": {"type": "cancel_pending", "message": "检测到摇头，已取消待确认任务"},
    },
    {
        "name": "语音打开记事本",
        "enabled": True,
        "tier_min": "lite",
        "trigger": {
            "type": "speech",
            "match": "打开记事本",
            "bypass_llm": False,
        },
        "action": {
            "type": "notify",
            "message": "检测到语音「打开记事本」，请由灵枢大脑规划执行（已禁用规则捷径）",
        },
    },
    {
        "name": "举手触发提醒",
        "enabled": False,
        "tier_min": "pro",
        "trigger": {
            "type": "gesture",
            "event": "hand_raised",
            "confidence_min": 0.5,
        },
        "action": {"type": "notify", "message": "检测到举手手势"},
    },
]


def ensure_perception_seed_rules() -> None:
    """补充手势/视觉默认规则（不覆盖用户已有规则）."""
    existing = {r.name for r in list_rules()}
    for item in _DEFAULT_RULES:
        if item["name"] in existing:
            continue
        create_rule(
            RuleCreate(
                name=item["name"],
                enabled=bool(item.get("enabled", False)),
                tier_min=item.get("tier_min", "lite"),
                trigger=RuleTrigger(**item["trigger"]),
                action=RuleAction(**item["action"]),
            )
        )


def seed_defaults() -> None:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM rules").fetchone()
        if row and row["c"] > 0:
            return
        for item in _DEFAULT_RULES:
            rule_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO rules (rule_id, name, enabled, tier_min, trigger_json, action_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    rule_id,
                    item["name"],
                    1 if item["enabled"] else 0,
                    item["tier_min"],
                    json.dumps(item["trigger"], ensure_ascii=False),
                    json.dumps(item["action"], ensure_ascii=False),
                ),
            )


def _row_to_rule(row) -> Rule:
    return Rule(
        rule_id=row["rule_id"],
        name=row["name"],
        enabled=bool(row["enabled"]),
        tier_min=row["tier_min"],
        trigger=RuleTrigger(**json.loads(row["trigger_json"])),
        action=RuleAction(**json.loads(row["action_json"])),
    )


def list_rules() -> list[Rule]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM rules ORDER BY created_at ASC").fetchall()
    return [_row_to_rule(r) for r in rows]


def get_rule(rule_id: str) -> Rule | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM rules WHERE rule_id = ?", (rule_id,)).fetchone()
    return _row_to_rule(row) if row else None


def create_rule(body: RuleCreate) -> Rule:
    rule_id = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO rules (rule_id, name, enabled, tier_min, trigger_json, action_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                rule_id,
                body.name,
                1 if body.enabled else 0,
                body.tier_min,
                json.dumps(body.trigger.model_dump(), ensure_ascii=False),
                json.dumps(body.action.model_dump(), ensure_ascii=False),
            ),
        )
    rule = get_rule(rule_id)
    assert rule
    return rule


def update_rule(rule_id: str, body: RuleCreate) -> Rule | None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE rules SET name=?, enabled=?, tier_min=?, trigger_json=?, action_json=?,
            updated_at=datetime('now') WHERE rule_id=?
            """,
            (
                body.name,
                1 if body.enabled else 0,
                body.tier_min,
                json.dumps(body.trigger.model_dump(), ensure_ascii=False),
                json.dumps(body.action.model_dump(), ensure_ascii=False),
                rule_id,
            ),
        )
    return get_rule(rule_id)


def delete_rule(rule_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM rules WHERE rule_id = ?", (rule_id,))
        return cur.rowcount > 0


def count_rules() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM rules").fetchone()
    return int(row["c"]) if row else 0
