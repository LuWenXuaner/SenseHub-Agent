"""用户积分、邀请、插件、账单（SQLite）."""

from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sensehub.db.database import get_connection
from sensehub.db import users as user_store

POINTS_SIGNIN_DAILY = 20
POINTS_SIGNIN_STREAK_BONUS = 50
POINTS_SIGNIN_STREAK_DAYS = 7
POINTS_INVITE_REGISTER = 100
POINTS_INVITE_MAX = 30
POINTS_INVITE_REBATE_PERCENT = 10

EXCHANGE_CATALOG: dict[str, dict[str, Any]] = {
    "tier-lite": {"cost": 800, "label": "Lite 档位 7 天", "category": "tier", "tier": "lite", "days": 7},
    "tier-pro": {"cost": 5000, "label": "Pro 档位 30 天", "category": "tier", "tier": "pro", "days": 30},
    "tier-max": {"cost": 20000, "label": "Max 档位 30 天", "category": "tier", "tier": "max", "days": 30},
    "sub-lite-month": {"cost": 800, "label": "Lite 月度套餐", "category": "tier", "tier": "lite", "days": 30},
    "sub-lite-year": {"cost": 8448, "label": "Lite 年度套餐", "category": "tier", "tier": "lite", "days": 365},
    "sub-standard-month": {"cost": 2500, "label": "Standard 月度套餐", "category": "tier", "tier": "pro", "days": 30},
    "sub-standard-year": {"cost": 26400, "label": "Standard 年度套餐", "category": "tier", "tier": "pro", "days": 365},
    "sub-pro-month": {"cost": 5000, "label": "Pro 月度套餐", "category": "tier", "tier": "pro", "days": 30},
    "sub-pro-year": {"cost": 52800, "label": "Pro 年度套餐", "category": "tier", "tier": "pro", "days": 365},
    "sub-max-month": {"cost": 20000, "label": "Max 月度套餐", "category": "tier", "tier": "max", "days": 30},
    "sub-max-year": {"cost": 211200, "label": "Max 年度套餐", "category": "tier", "tier": "max", "days": 365},
    "api-qwen": {"cost": 800, "label": "Qwen3 100 万 Token", "category": "api"},
    "api-doubao": {"cost": 600, "label": "Doubao 100 万 Token", "category": "api"},
    "api-deepseek": {"cost": 700, "label": "DeepSeek-V3 80 万 Token", "category": "api"},
    "api-qwen-vl": {"cost": 1200, "label": "Qwen2.5-VL 50 万 Token", "category": "api"},
    "api-whisper": {"cost": 500, "label": "语音识别 120 分钟", "category": "api"},
    "code-agent-boost": {"cost": 1500, "label": "Code Agent 加量包", "category": "product"},
    "plugin-web": {"cost": 900, "label": "联网插件 30 天", "category": "product", "plugin_id": "web", "days": 30},
    "storage-workspace": {"cost": 400, "label": "工作区扩容 5 GB", "category": "product"},
    "api-tts": {"cost": 450, "label": "语音合成 30 万字符", "category": "api"},
}

PLUGIN_CATALOG = [
    {"id": "web", "name": "联网插件", "desc": "搜索与网页解析"},
    {"id": "wake", "name": "唤醒词", "desc": "语音唤醒 Console"},
    {"id": "vision", "name": "视觉插件", "desc": "摄像头与 VLM"},
    {"id": "code", "name": "Code Agent", "desc": "灵枢 Code 文件助手"},
    {"id": "tts", "name": "语音播报", "desc": "执行结果 TTS 反馈"},
]

DEFAULT_PLUGINS = {"web": False, "wake": True, "vision": True, "code": True, "tts": False}

LEDGER_TYPE_LABELS = {
    "checkin": "每日签到",
    "checkin_bonus": "连续签到奖励",
    "invite_signup": "邀请注册奖励",
    "invite_rebate": "邀请返利",
    "redeem": "积分兑换",
    "subscribe": "订阅套餐",
    "bonus": "管理员发放",
    "wheel_spin": "幸运转盘",
    "wheel_prize": "转盘奖励",
    "achievement": "成就奖励",
    "milestone": "等级里程碑",
}

TIER_RANK = {"lite": 0, "pro": 1, "max": 2}


def _effective_wallet_tier(wallet: dict[str, Any]) -> tuple[str, bool]:
    """返回 (有效档位, 是否处于付费订阅期内)."""
    tier = str(wallet.get("tier") or "lite")
    expires = wallet.get("tier_expires_at")
    if expires and str(expires) < _today():
        return "lite", False
    if tier in ("pro", "max"):
        return tier, True
    if tier == "lite" and expires and str(expires) >= _today():
        return "lite", True
    return "lite", False


def _validate_tier_subscription(wallet: dict[str, Any], target_tier: str) -> str:
    """校验档位订阅，返回 new / renew / upgrade."""
    if target_tier not in TIER_RANK:
        raise ValueError("无效档位")
    current, active = _effective_wallet_tier(wallet)
    cur_rank = TIER_RANK[current]
    tgt_rank = TIER_RANK[target_tier]
    if active and tgt_rank < cur_rank:
        names = {"lite": "Lite", "pro": "Pro", "max": "Max"}
        raise ValueError(f"当前 {names.get(current, current)} 套餐未到期，无法订阅更低档位")
    if active and tgt_rank == cur_rank:
        return "renew"
    if active and tgt_rank > cur_rank:
        return "upgrade"
    return "new"


def _compute_tier_expiry(wallet: dict[str, Any], target_tier: str, days: int, action: str) -> str:
    expires = wallet.get("tier_expires_at")
    current, _ = _effective_wallet_tier(wallet)
    if action == "renew" and current == target_tier and expires and str(expires) >= _today():
        base = date.fromisoformat(str(expires))
    else:
        base = date.today()
    return (base + timedelta(days=int(days))).isoformat()


def get_subscription_status(username: str) -> dict[str, Any]:
    wallet = get_wallet_by_username(username)
    if not wallet:
        return {"tier": "lite", "effective_tier": "lite", "active": False, "tier_expires_at": None, "tier_rank": 0}
    effective, active = _effective_wallet_tier(wallet)
    return {
        "tier": wallet.get("tier") or "lite",
        "effective_tier": effective,
        "active": active,
        "tier_expires_at": wallet.get("tier_expires_at"),
        "tier_rank": TIER_RANK.get(effective, 0),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return date.today().isoformat()


def _username_to_user_id(username: str) -> str | None:
    user = user_store.get_user(username.strip().lower())
    return user["user_id"] if user else None


def _generate_public_id(conn) -> str:
    for _ in range( 20):
        pid = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
        row = conn.execute("SELECT 1 FROM user_wallets WHERE public_id = ?", (pid,)).fetchone()
        if not row:
            return pid
    return str(uuid.uuid4().int % 10_000_000_000)


def _generate_invite_code(conn) -> str:
    for _ in range(30):
        code = "SH" + secrets.token_hex(4).upper()
        row = conn.execute("SELECT 1 FROM user_wallets WHERE invite_code = ?", (code,)).fetchone()
        if not row:
            return code
    return "SH" + uuid.uuid4().hex[:8].upper()


def ensure_wallet(user_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM user_wallets WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return dict(row)
        public_id = _generate_public_id(conn)
        invite_code = _generate_invite_code(conn)
        conn.execute(
            """
            INSERT INTO user_wallets (
                user_id, public_id, invite_code, points_balance, total_earned,
                total_spent, checkin_streak, tier, tier_expires_at
            ) VALUES (?, ?, ?, 0, 0, 0, 0, 'lite', NULL)
            """,
            (user_id, public_id, invite_code),
        )
        for pid, enabled in DEFAULT_PLUGINS.items():
            conn.execute(
                """
                INSERT INTO user_plugins (user_id, plugin_id, enabled, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, pid, 1 if enabled else 0, _now_iso()),
            )
        row = conn.execute("SELECT * FROM user_wallets WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row)


def get_wallet_by_username(username: str) -> dict[str, Any] | None:
    user_id = _username_to_user_id(username)
    if not user_id:
        return None
    return ensure_wallet(user_id)


def get_wallet_by_invite_code(code: str) -> dict[str, Any] | None:
    code = code.strip().upper()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM user_wallets WHERE invite_code = ?", (code,)).fetchone()
    return dict(row) if row else None


def _add_ledger(
    conn,
    user_id: str,
    delta: int,
    entry_type: str,
    *,
    note: str = "",
    ref_id: str = "",
) -> int:
    row = conn.execute("SELECT points_balance, total_earned, total_spent FROM user_wallets WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        raise ValueError("钱包不存在")
    balance = int(row["points_balance"]) + delta
    if balance < 0:
        raise ValueError("积分不足")
    earned = int(row["total_earned"]) + (delta if delta > 0 else 0)
    spent = int(row["total_spent"]) + (abs(delta) if delta < 0 else 0)
    conn.execute(
        """
        UPDATE user_wallets
        SET points_balance = ?, total_earned = ?, total_spent = ?
        WHERE user_id = ?
        """,
        (balance, earned, spent, user_id),
    )
    cur = conn.execute(
        """
        INSERT INTO points_ledger (user_id, delta, balance_after, entry_type, note, ref_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, delta, balance, entry_type, note, ref_id),
    )
    return int(cur.lastrowid)


def check_in(username: str) -> dict[str, Any]:
    user_id = _username_to_user_id(username)
    if not user_id:
        raise ValueError("用户不存在")
    wallet = ensure_wallet(user_id)
    today = _today()
    if wallet.get("last_checkin_date") == today:
        return {"ok": False, "earned": 0, "balance": wallet["points_balance"]}

    earned = POINTS_SIGNIN_DAILY
    streak = int(wallet.get("checkin_streak") or 0) + 1
    bonus = 0
    if streak >= POINTS_SIGNIN_STREAK_DAYS and streak % POINTS_SIGNIN_STREAK_DAYS == 0:
        bonus = POINTS_SIGNIN_STREAK_BONUS
        earned += bonus

    from sensehub.db.gamification import is_weekend_double, on_checkin

    weekend = is_weekend_double()
    daily_pts = POINTS_SIGNIN_DAILY * (2 if weekend else 1)
    earned = daily_pts + bonus

    with get_connection() as conn:
        note = "每日签到（周末双倍）" if weekend else "每日签到"
        _add_ledger(conn, user_id, daily_pts, "checkin", note=note)
        if bonus:
            _add_ledger(conn, user_id, bonus, "checkin_bonus", note=f"连续签到 {POINTS_SIGNIN_STREAK_DAYS} 天")
        conn.execute(
            """
            UPDATE user_wallets SET last_checkin_date = ?, checkin_streak = ? WHERE user_id = ?
            """,
            (today, streak, user_id),
        )
        row = conn.execute("SELECT points_balance FROM user_wallets WHERE user_id = ?", (user_id,)).fetchone()
    on_checkin(user_id, weekend=weekend)
    return {
        "ok": True,
        "earned": earned,
        "balance": int(row["points_balance"]),
        "streak": streak,
        "weekend_double": weekend,
    }


def redeem_item(username: str, item_id: str) -> dict[str, Any]:
    item = EXCHANGE_CATALOG.get(item_id)
    if not item:
        raise ValueError("兑换项不存在")
    user_id = _username_to_user_id(username)
    if not user_id:
        raise ValueError("用户不存在")
    wallet = ensure_wallet(user_id)
    cost = int(item["cost"])
    label = str(item["label"])

    if int(wallet.get("points_balance") or 0) < cost:
        raise ValueError("积分不足")

    tier_action = "new"
    target_tier = item.get("tier")
    if target_tier:
        tier_action = _validate_tier_subscription(wallet, str(target_tier))

    with get_connection() as conn:
        wallet_row = conn.execute("SELECT * FROM user_wallets WHERE user_id = ?", (user_id,)).fetchone()
        wallet = dict(wallet_row) if wallet_row else wallet

        _add_ledger(conn, user_id, -cost, "redeem", note=label, ref_id=item_id)
        conn.execute(
            """
            INSERT INTO exchange_records (user_id, item_id, item_label, cost)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, item_id, label, cost),
        )
        conn.execute(
            """
            INSERT INTO usage_bills (user_id, bill_date, category, description, amount, unit, points_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, _today(), item.get("category", "product"), label, cost, "积分", cost),
        )
        if target_tier:
            expires = _compute_tier_expiry(
                wallet, str(target_tier), int(item.get("days", 30)), tier_action
            )
            conn.execute(
                "UPDATE user_wallets SET tier = ?, tier_expires_at = ? WHERE user_id = ?",
                (target_tier, expires, user_id),
            )
        if item.get("plugin_id"):
            conn.execute(
                """
                INSERT INTO user_plugins (user_id, plugin_id, enabled, updated_at)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(user_id, plugin_id) DO UPDATE SET enabled = 1, updated_at = excluded.updated_at
                """,
                (user_id, item["plugin_id"], _now_iso()),
            )
        _apply_invite_rebate(conn, user_id, cost, label)
        row = conn.execute(
            "SELECT points_balance, tier, tier_expires_at FROM user_wallets WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    result = {
        "ok": True,
        "item_id": item_id,
        "label": label,
        "cost": cost,
        "balance": int(row["points_balance"]),
    }
    if target_tier:
        result["tier_action"] = tier_action
        result["tier"] = str(row["tier"] or target_tier)
        result["tier_expires_at"] = row["tier_expires_at"]
        sub = get_subscription_status(username)
        result["subscription_active"] = bool(sub.get("active"))
    return result


def subscribe_plan(username: str, plan: str = "pro") -> dict[str, Any]:
    mapping = {
        "lite": "sub-lite-month",
        "lite-monthly": "sub-lite-month",
        "lite-month": "sub-lite-month",
        "lite-yearly": "sub-lite-year",
        "lite-year": "sub-lite-year",
        "standard": "sub-standard-month",
        "standard-monthly": "sub-standard-month",
        "standard-month": "sub-standard-month",
        "standard-yearly": "sub-standard-year",
        "standard-year": "sub-standard-year",
        "pro": "sub-pro-month",
        "pro-monthly": "sub-pro-month",
        "pro-month": "sub-pro-month",
        "pro-yearly": "sub-pro-year",
        "pro-year": "sub-pro-year",
        "max": "sub-max-month",
        "max-monthly": "sub-max-month",
        "max-month": "sub-max-month",
        "max-yearly": "sub-max-year",
        "max-year": "sub-max-year",
    }
    item_id = mapping.get(plan.lower(), "sub-pro-month")
    result = redeem_item(username, item_id)
    with get_connection() as conn:
        user_id = _username_to_user_id(username)
        if user_id:
            _add_ledger(conn, user_id, 0, "subscribe", note=f"订阅 {plan}", ref_id=plan)
    return result


def list_subscription_plans() -> list[dict[str, Any]]:
    """公开订阅档位目录（积分价）."""
    specs = [
        ("lite", "sub-lite-month", "sub-lite-year", 800),
        ("standard", "sub-standard-month", "sub-standard-year", 2500),
        ("pro", "sub-pro-month", "sub-pro-year", 5000),
        ("max", "sub-max-month", "sub-max-year", 20000),
    ]
    items: list[dict[str, Any]] = []
    for tier_id, month_id, year_id, month_cost in specs:
        month = EXCHANGE_CATALOG[month_id]
        year = EXCHANGE_CATALOG[year_id]
        items.append(
            {
                "id": tier_id,
                "effective_tier": month["tier"],
                "tier_rank": TIER_RANK.get(str(month["tier"]), 0),
                "monthly_item_id": month_id,
                "yearly_item_id": year_id,
                "monthly_cost": month_cost,
                "yearly_cost": int(year["cost"]),
                "yearly_save": month_cost * 12 - int(year["cost"]),
                "monthly_days": int(month.get("days", 30)),
                "yearly_days": int(year.get("days", 365)),
                "tier": month["tier"],
                "monthly_label": month["label"],
                "yearly_label": year["label"],
            }
        )
    return items


def _apply_invite_rebate(conn, invitee_user_id: str, cost: int, label: str) -> None:
    row = conn.execute(
        "SELECT invited_by_user_id FROM user_wallets WHERE user_id = ?", (invitee_user_id,)
    ).fetchone()
    if not row or not row["invited_by_user_id"]:
        return
    inviter_id = row["invited_by_user_id"]
    rebate = max(1, int(cost * POINTS_INVITE_REBATE_PERCENT / 100))
    _add_ledger(conn, inviter_id, rebate, "invite_rebate", note=f"好友兑换：{label}", ref_id=invitee_user_id)


def process_signup_invite(invitee_user_id: str, invite_code: str) -> None:
    invite_code = invite_code.strip().upper()
    if not invite_code:
        return
    inviter_wallet = get_wallet_by_invite_code(invite_code)
    if not inviter_wallet or inviter_wallet["user_id"] == invitee_user_id:
        return

    inviter_id = inviter_wallet["user_id"]
    with get_connection() as conn:
        count_row = conn.execute(
            """
            SELECT COUNT(*) AS c FROM invite_records
            WHERE inviter_user_id = ? AND status = 'registered'
            """,
            (inviter_id,),
        ).fetchone()
        if int(count_row["c"]) >= POINTS_INVITE_MAX:
            return

        conn.execute(
            "UPDATE user_wallets SET invited_by_user_id = ? WHERE user_id = ?",
            (inviter_id, invitee_user_id),
        )
        conn.execute(
            """
            INSERT INTO invite_records (inviter_user_id, invitee_user_id, invite_code, status, registered_at)
            VALUES (?, ?, ?, 'registered', ?)
            """,
            (inviter_id, invitee_user_id, invite_code, _now_iso()),
        )
        _add_ledger(conn, inviter_id, POINTS_INVITE_REGISTER, "invite_signup", note="邀请好友注册", ref_id=invitee_user_id)
        _add_ledger(conn, invitee_user_id, POINTS_INVITE_REGISTER, "invite_signup", note="受邀注册奖励", ref_id=inviter_id)


def get_summary(username: str) -> dict[str, Any]:
    wallet = get_wallet_by_username(username)
    if not wallet:
        raise ValueError("用户不存在")
    today = _today()
    can_checkin = wallet.get("last_checkin_date") != today
    effective, sub_active = _effective_wallet_tier(wallet)
    return {
        "public_id": wallet["public_id"],
        "invite_code": wallet["invite_code"],
        "balance": int(wallet["points_balance"]),
        "total_earned": int(wallet["total_earned"]),
        "total_spent": int(wallet["total_spent"]),
        "can_checkin": can_checkin,
        "checkin_streak": int(wallet.get("checkin_streak") or 0),
        "tier": effective,
        "tier_expires_at": wallet.get("tier_expires_at"),
        "subscription_active": sub_active,
        "tier_rank": TIER_RANK.get(effective, 0),
    }


def list_ledger(username: str, *, filter_type: str = "all", limit: int = 100) -> list[dict[str, Any]]:
    user_id = _username_to_user_id(username)
    if not user_id:
        return []
    sql = """
        SELECT id, delta, balance_after, entry_type, note, ref_id, created_at
        FROM points_ledger WHERE user_id = ?
    """
    params: list[Any] = [user_id]
    if filter_type == "earn":
        sql += " AND delta > 0"
    elif filter_type == "spend":
        sql += " AND delta < 0"
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def list_exchanges(username: str, limit: int = 100) -> list[dict[str, Any]]:
    user_id = _username_to_user_id(username)
    if not user_id:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, item_id, item_label, cost, created_at
            FROM exchange_records WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_bills(username: str, limit: int = 100) -> list[dict[str, Any]]:
    user_id = _username_to_user_id(username)
    if not user_id:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, bill_date, category, description, amount, unit, points_cost, created_at
            FROM usage_bills WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def bills_summary(username: str) -> dict[str, Any]:
    user_id = _username_to_user_id(username)
    if not user_id:
        return {"total_spent": 0, "token_usage": 0, "asr_seconds": 0, "plugin_calls": 0}
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(points_cost), 0) AS total
            FROM usage_bills WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    total = int(row["total"]) if row else 0
    from sensehub.db.token_usage import token_usage_summary

    usage = token_usage_summary(username)
    return {
        "total_spent": total,
        "token_usage": int(usage.get("total_tokens") or 0),
        "asr_seconds": 0,
        "plugin_calls": int(usage.get("request_count") or 0),
    }


def invite_stats(username: str) -> dict[str, Any]:
    user_id = _username_to_user_id(username)
    if not user_id:
        return {"invited": 0, "earned": 0, "pending": 0, "rebate_total": 0}
    wallet = ensure_wallet(user_id)
    with get_connection() as conn:
        invited = conn.execute(
            "SELECT COUNT(*) AS c FROM invite_records WHERE inviter_user_id = ? AND status = 'registered'",
            (user_id,),
        ).fetchone()
        earned_row = conn.execute(
            """
            SELECT COALESCE(SUM(delta), 0) AS s FROM points_ledger
            WHERE user_id = ? AND entry_type IN ('invite_signup', 'invite_rebate')
            """,
            (user_id,),
        ).fetchone()
        rebate_row = conn.execute(
            """
            SELECT COALESCE(SUM(delta), 0) AS s FROM points_ledger
            WHERE user_id = ? AND entry_type = 'invite_rebate'
            """,
            (user_id,),
        ).fetchone()
        pending = conn.execute(
            "SELECT COUNT(*) AS c FROM invite_records WHERE inviter_user_id = ? AND status = 'pending'",
            (user_id,),
        ).fetchone()
    return {
        "invited": int(invited["c"]),
        "earned": int(earned_row["s"]),
        "pending": int(pending["c"]),
        "rebate_total": int(rebate_row["s"]),
        "invite_code": wallet["invite_code"],
        "quota": POINTS_INVITE_MAX,
    }


def list_invites(username: str, limit: int = 50) -> list[dict[str, Any]]:
    user_id = _username_to_user_id(username)
    if not user_id:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT ir.id, ir.invite_code, ir.status, ir.registered_at, ir.created_at,
                   w.public_id AS invitee_public_id
            FROM invite_records ir
            LEFT JOIN user_wallets w ON w.user_id = ir.invitee_user_id
            WHERE ir.inviter_user_id = ?
            ORDER BY ir.id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        item["invitee_id"] = item.pop("invitee_public_id") or "—"
        out.append(item)
    return out


def get_user_tier(username: str) -> str:
    wallet = get_wallet_by_username(username)
    if not wallet:
        return "lite"
    tier = str(wallet.get("tier") or "lite")
    expires = wallet.get("tier_expires_at")
    if expires and expires < _today():
        return "lite"
    if tier in ("lite", "pro", "max"):
        return tier
    return "lite"


def list_plugins(username: str) -> list[dict[str, Any]]:
    user_id = _username_to_user_id(username)
    if not user_id:
        return []
    ensure_wallet(user_id)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT plugin_id, enabled, updated_at FROM user_plugins WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    enabled_map = {r["plugin_id"]: bool(r["enabled"]) for r in rows}
    out = []
    for meta in PLUGIN_CATALOG:
        out.append({**meta, "enabled": enabled_map.get(meta["id"], False)})
    return out


def set_plugin_enabled(username: str, plugin_id: str, enabled: bool) -> dict[str, Any]:
    valid = {p["id"] for p in PLUGIN_CATALOG}
    if plugin_id not in valid:
        raise ValueError("未知插件")
    user_id = _username_to_user_id(username)
    if not user_id:
        raise ValueError("用户不存在")
    ensure_wallet(user_id)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_plugins (user_id, plugin_id, enabled, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, plugin_id) DO UPDATE SET enabled = excluded.enabled, updated_at = excluded.updated_at
            """,
            (user_id, plugin_id, 1 if enabled else 0, _now_iso()),
        )
    return {"id": plugin_id, "enabled": enabled}


def is_plugin_enabled(username: str, plugin_id: str) -> bool:
    user_id = _username_to_user_id(username)
    if not user_id:
        return False
    with get_connection() as conn:
        row = conn.execute(
            "SELECT enabled FROM user_plugins WHERE user_id = ? AND plugin_id = ?",
            (user_id, plugin_id),
        ).fetchone()
    if row is None:
        return DEFAULT_PLUGINS.get(plugin_id, False)
    return bool(row["enabled"])


def admin_grant_points(admin_username: str, target_user_id: str, amount: int, note: str = "") -> dict[str, Any]:
    """管理员给指定用户发放积分."""
    if admin_username.lower() != "admin":
        raise PermissionError("需要管理员权限")
    if amount <= 0:
        raise ValueError("积分数量必须大于 0")
    user = user_store.get_user_by_id(target_user_id.strip())
    if not user:
        raise ValueError("用户不存在")
    user_id = user["user_id"]
    ensure_wallet(user_id)
    ledger_note = note.strip() or "管理员发放"
    with get_connection() as conn:
        _add_ledger(conn, user_id, amount, "bonus", note=ledger_note, ref_id=admin_username)
        row = conn.execute(
            "SELECT points_balance FROM user_wallets WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return {
        "ok": True,
        "user_id": user_id,
        "username": user["username"],
        "amount": amount,
        "balance": int(row["points_balance"]),
    }
