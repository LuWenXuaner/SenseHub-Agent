"""积分游戏化：等级、成就、转盘、排行榜、赛季与个性化."""

from __future__ import annotations

import json
import random
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sensehub.db.database import get_connection
from sensehub.db import wallet as wallet_store

WHEEL_COST_POINTS = 30
WHEEL_FREE_DAILY = 1
WHEEL_SUBSCRIBER_EXTRA = 1

LEVEL_THRESHOLDS = [0, 100, 300, 600, 1000, 1500, 2200, 3000, 4000, 5200, 6600, 8200, 10000, 12000, 14500, 17500, 21000, 25000, 30000, 36000]

RATING_BY_LEVEL = [
    (1, 3, "bronze", "青铜"),
    (4, 7, "silver", "白银"),
    (8, 12, "gold", "黄金"),
    (13, 16, "platinum", "铂金"),
    (17, 20, "diamond", "钻石"),
]

ACHIEVEMENTS: dict[str, dict[str, Any]] = {
    "first_checkin": {"name": "初来乍到", "desc": "完成首次签到", "icon": "sunrise", "xp": 20, "points": 10},
    "streak_7": {"name": "七日恒心", "desc": "连续签到 7 天", "icon": "flame", "xp": 50, "points": 30},
    "streak_30": {"name": "月度坚守", "desc": "连续签到 30 天", "icon": "calendar", "xp": 120, "points": 100},
    "invite_1": {"name": "引路人", "desc": "成功邀请 1 位好友", "icon": "users", "xp": 40, "points": 20},
    "invite_5": {"name": "社交达人", "desc": "成功邀请 5 位好友", "icon": "share", "xp": 100, "points": 80},
    "earn_1k": {"name": "小有积蓄", "desc": "累计获得 1000 积分", "icon": "coins", "xp": 30, "points": 0},
    "earn_10k": {"name": "积分富翁", "desc": "累计获得 10000 积分", "icon": "gem", "xp": 150, "points": 50},
    "wheel_first": {"name": "试试手气", "desc": "完成首次转盘抽奖", "icon": "dice", "xp": 20, "points": 0},
    "subscriber": {"name": "尊贵会员", "desc": "订阅任意付费套餐", "icon": "crown", "xp": 80, "points": 0},
    "weekend_hero": {"name": "周末战士", "desc": "在周末双倍活动中签到 4 次", "icon": "sparkles", "xp": 60, "points": 40},
}

WHEEL_PRIZES: list[dict[str, Any]] = [
    {"id": "p5", "label": "5 积分", "points": 5, "weight": 28},
    {"id": "p10", "label": "10 积分", "points": 10, "weight": 24},
    {"id": "p20", "label": "20 积分", "points": 20, "weight": 20},
    {"id": "p50", "label": "50 积分", "points": 50, "weight": 14},
    {"id": "p100", "label": "100 积分", "points": 100, "weight": 9},
    {"id": "p200", "label": "200 积分", "points": 200, "weight": 4},
    {"id": "p500", "label": "500 积分", "points": 500, "weight": 1},
]

BACKGROUNDS: dict[str, dict[str, Any]] = {
    "default": {"name": "默认暖白", "unlock": "level", "min_level": 1},
    "aurora": {"name": "极光紫雾", "unlock": "level", "min_level": 3},
    "sunset": {"name": "落日金辉", "unlock": "level", "min_level": 5},
    "ocean": {"name": "深海蔚蓝", "unlock": "achievement", "achievement_id": "earn_1k"},
    "midnight": {"name": "午夜星辰", "unlock": "tier", "min_tier": "pro"},
    "max_gold": {"name": "鎏金殿堂", "unlock": "tier", "min_tier": "max"},
}

THEMES: dict[str, dict[str, Any]] = {
    "default": {"name": "经典米白", "accent": "#c9a96e"},
    "ocean": {"name": "海洋清风", "accent": "#1677ff"},
    "forest": {"name": "森林绿意", "accent": "#389e0d"},
    "rose": {"name": "玫瑰暮光", "accent": "#eb2f96"},
    "violet": {"name": "紫晶幻境", "unlock": "level", "min_level": 8},
    "ember": {"name": "炽焰橙光", "unlock": "tier", "min_tier": "pro"},
}

MILESTONES = [
    {"level": 5, "points": 50, "label": "Lv.5 里程碑"},
    {"level": 10, "points": 120, "label": "Lv.10 里程碑"},
    {"level": 15, "points": 200, "label": "Lv.15 里程碑"},
    {"level": 20, "points": 500, "label": "Lv.20 里程碑"},
]

SEASONS = [
    {"id": "2026-s1", "name": "2026 春日赛季", "start": "2026-03-01", "end": "2026-05-31", "bonus_tag": "spring"},
    {"id": "2026-s2", "name": "2026 夏日赛季", "start": "2026-06-01", "end": "2026-08-31", "bonus_tag": "summer"},
    {"id": "2026-s3", "name": "2026 秋日赛季", "start": "2026-09-01", "end": "2026-11-30", "bonus_tag": "autumn"},
    {"id": "2026-s4", "name": "2026 冬日赛季", "start": "2026-12-01", "end": "2027-02-28", "bonus_tag": "winter"},
]


def _today() -> str:
    return date.today().isoformat()


def _username_to_user_id(username: str) -> str | None:
    from sensehub.db import users as user_store

    user = user_store.get_user(username.strip().lower())
    return str(user["user_id"]) if user else None


def is_weekend_double() -> bool:
    return date.today().weekday() >= 5


def current_season() -> dict[str, Any]:
    today = _today()
    for season in SEASONS:
        if season["start"] <= today <= season["end"]:
            return {**season, "active": True}
    return {"id": "off", "name": "休赛期", "active": False, "start": "", "end": "", "bonus_tag": ""}


def xp_to_level(xp: int) -> int:
    level = 1
    for idx, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            level = idx + 1
    return min(level, len(LEVEL_THRESHOLDS))


def level_progress(xp: int) -> dict[str, Any]:
    level = xp_to_level(xp)
    current_floor = LEVEL_THRESHOLDS[level - 1] if level > 0 else 0
    next_cap = LEVEL_THRESHOLDS[level] if level < len(LEVEL_THRESHOLDS) else LEVEL_THRESHOLDS[-1] + 5000
    span = max(1, next_cap - current_floor)
    pct = int(min(100, max(0, round((xp - current_floor) / span * 100))))
    rating = RATING_BY_LEVEL[0]
    for lo, hi, rid, rname in RATING_BY_LEVEL:
        if lo <= level <= hi:
            rating = (rid, rname)
            break
    return {
        "level": level,
        "xp": xp,
        "current_floor": current_floor,
        "next_cap": next_cap,
        "progress_pct": pct,
        "rating_id": rating[0],
        "rating_name": rating[1],
        "max_level": len(LEVEL_THRESHOLDS),
    }


def ensure_profile(user_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM user_gamification WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return dict(row)
        conn.execute(
            """
            INSERT INTO user_gamification (user_id, xp, level, profile_bg, profile_theme, milestone_claimed_json, weekend_checkins)
            VALUES (?, 0, 1, 'default', 'default', '[]', 0)
            """,
            (user_id,),
        )
        row = conn.execute("SELECT * FROM user_gamification WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else {}


def _wallet_stats(user_id: str) -> dict[str, Any]:
    wallet = wallet_store.ensure_wallet(user_id)
    with get_connection() as conn:
        invite_count = conn.execute(
            "SELECT COUNT(*) FROM invite_records WHERE inviter_user_id = ? AND status = 'registered'",
            (user_id,),
        ).fetchone()[0]
        spin_count = conn.execute("SELECT COUNT(*) FROM wheel_spins WHERE user_id = ?", (user_id,)).fetchone()[0]
        achievements = {
            r["achievement_id"]
            for r in conn.execute(
                "SELECT achievement_id FROM user_achievements WHERE user_id = ?", (user_id,)
            ).fetchall()
        }
    effective, active = wallet_store._effective_wallet_tier(wallet)
    return {
        "wallet": wallet,
        "invite_count": int(invite_count or 0),
        "spin_count": int(spin_count or 0),
        "achievements": achievements,
        "subscription_active": active,
        "tier": effective,
    }


def _grant_points(conn, user_id: str, points: int, entry_type: str, note: str) -> None:
    if points == 0:
        return
    wallet_store._add_ledger(conn, user_id, points, entry_type, note=note)


def _add_xp(conn, user_id: str, xp_delta: int) -> dict[str, Any]:
    profile = ensure_profile(user_id)
    new_xp = int(profile.get("xp") or 0) + xp_delta
    new_level = xp_to_level(new_xp)
    conn.execute(
        "UPDATE user_gamification SET xp = ?, level = ?, updated_at = datetime('now') WHERE user_id = ?",
        (new_xp, new_level, user_id),
    )
    claimed = json.loads(str(profile.get("milestone_claimed_json") or "[]"))
    rewards: list[dict[str, Any]] = []
    for ms in MILESTONES:
        key = f"lv{ms['level']}"
        if new_level >= ms["level"] and key not in claimed:
            claimed.append(key)
            _grant_points(conn, user_id, int(ms["points"]), "milestone", ms["label"])
            rewards.append(ms)
    if rewards:
        conn.execute(
            "UPDATE user_gamification SET milestone_claimed_json = ? WHERE user_id = ?",
            (json.dumps(claimed), user_id),
        )
    return {"xp": new_xp, "level": new_level, "milestone_rewards": rewards}


def unlock_achievement(conn, user_id: str, achievement_id: str) -> dict[str, Any] | None:
    if achievement_id not in ACHIEVEMENTS:
        return None
    exists = conn.execute(
        "SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
        (user_id, achievement_id),
    ).fetchone()
    if exists:
        return None
    meta = ACHIEVEMENTS[achievement_id]
    conn.execute(
        "INSERT INTO user_achievements (user_id, achievement_id) VALUES (?, ?)",
        (user_id, achievement_id),
    )
    xp = int(meta.get("xp") or 0)
    pts = int(meta.get("points") or 0)
    if pts:
        _grant_points(conn, user_id, pts, "achievement", meta["name"])
    level_info = _add_xp(conn, user_id, xp) if xp else {}
    return {"id": achievement_id, **meta, "level_info": level_info}


def evaluate_achievements(user_id: str) -> list[dict[str, Any]]:
    stats = _wallet_stats(user_id)
    wallet = stats["wallet"]
    streak = int(wallet.get("checkin_streak") or 0)
    earned = int(wallet.get("total_earned") or 0)
    unlocked: list[dict[str, Any]] = []
    checks: list[tuple[str, bool]] = [
        ("first_checkin", bool(wallet.get("last_checkin_date"))),
        ("streak_7", streak >= 7),
        ("streak_30", streak >= 30),
        ("invite_1", stats["invite_count"] >= 1),
        ("invite_5", stats["invite_count"] >= 5),
        ("earn_1k", earned >= 1000),
        ("earn_10k", earned >= 10000),
        ("wheel_first", stats["spin_count"] >= 1),
        ("subscriber", stats["subscription_active"]),
        ("weekend_hero", int(ensure_profile(user_id).get("weekend_checkins") or 0) >= 4),
    ]
    with get_connection() as conn:
        for aid, ok in checks:
            if not ok or aid in stats["achievements"]:
                continue
            row = unlock_achievement(conn, user_id, aid)
            if row:
                unlocked.append(row)
    return unlocked


def sync_xp_from_wallet(user_id: str) -> dict[str, Any]:
    wallet = wallet_store.ensure_wallet(user_id)
    base_xp = int(wallet.get("total_earned") or 0) // 2
    with get_connection() as conn:
        profile = ensure_profile(user_id)
        bonus = 0
        for row in conn.execute(
            "SELECT achievement_id FROM user_achievements WHERE user_id = ?", (user_id,)
        ).fetchall():
            bonus += int(ACHIEVEMENTS.get(row["achievement_id"], {}).get("xp") or 0)
        xp = base_xp + bonus
        level = xp_to_level(xp)
        conn.execute(
            "UPDATE user_gamification SET xp = ?, level = ?, updated_at = datetime('now') WHERE user_id = ?",
            (xp, level, user_id),
        )
    return level_progress(xp)


def on_checkin(user_id: str, *, weekend: bool) -> None:
    with get_connection() as conn:
        if weekend:
            conn.execute(
                "UPDATE user_gamification SET weekend_checkins = COALESCE(weekend_checkins, 0) + 1 WHERE user_id = ?",
                (user_id,),
            )
        _add_xp(conn, user_id, 15)
    evaluate_achievements(user_id)


def wheel_status(username: str) -> dict[str, Any]:
    user_id = _username_to_user_id(username)
    if not user_id:
        raise ValueError("用户不存在")
    wallet = wallet_store.ensure_wallet(user_id)
    today = _today()
    sub = wallet_store.get_subscription_status(username)
    free_limit = WHEEL_FREE_DAILY + (WHEEL_SUBSCRIBER_EXTRA if sub.get("active") else 0)
    with get_connection() as conn:
        used_free = conn.execute(
            "SELECT COUNT(*) FROM wheel_spins WHERE user_id = ? AND spin_date = ? AND cost = 0",
            (user_id, today),
        ).fetchone()[0]
    return {
        "free_spins_left": max(0, free_limit - int(used_free or 0)),
        "spin_cost": WHEEL_COST_POINTS,
        "balance": int(wallet.get("points_balance") or 0),
        "prizes": [{"id": p["id"], "label": p["label"], "points": p["points"]} for p in WHEEL_PRIZES],
    }


def spin_wheel(username: str) -> dict[str, Any]:
    user_id = _username_to_user_id(username)
    if not user_id:
        raise ValueError("用户不存在")
    status = wheel_status(username)
    cost = 0
    if status["free_spins_left"] > 0:
        cost = 0
    else:
        cost = WHEEL_COST_POINTS
        if status["balance"] < cost:
            raise ValueError("积分不足，无法继续抽奖")

    prize = random.choices(WHEEL_PRIZES, weights=[p["weight"] for p in WHEEL_PRIZES], k=1)[0]
    today = _today()

    with get_connection() as conn:
        if cost:
            _grant_points(conn, user_id, -cost, "wheel_spin", "幸运转盘")
        _grant_points(conn, user_id, int(prize["points"]), "wheel_prize", prize["label"])
        conn.execute(
            """
            INSERT INTO wheel_spins (user_id, prize_id, prize_label, points_won, cost, spin_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, prize["id"], prize["label"], int(prize["points"]), cost, today),
        )
        _add_xp(conn, user_id, 5)
        unlock_achievement(conn, user_id, "wheel_first")

    evaluate_achievements(user_id)
    wallet = wallet_store.ensure_wallet(user_id)
    return {
        "prize": {"id": prize["id"], "label": prize["label"], "points": prize["points"]},
        "cost": cost,
        "balance": int(wallet.get("points_balance") or 0),
    }


def leaderboard(limit: int = 20) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT w.public_id, w.total_earned, g.level, g.xp, u.display_name
            FROM user_wallets w
            LEFT JOIN user_gamification g ON g.user_id = w.user_id
            LEFT JOIN users u ON u.user_id = w.user_id
            ORDER BY w.total_earned DESC, g.level DESC
            LIMIT ?
            """,
            (max(1, min(limit, 50)),),
        ).fetchall()
    out = []
    for idx, row in enumerate(rows, start=1):
        xp = int(row["xp"] or 0)
        prog = level_progress(xp if xp else int(row["total_earned"] or 0) // 2)
        out.append(
            {
                "rank": idx,
                "public_id": row["public_id"],
                "display_name": (row["display_name"] or row["public_id"] or "—")[:24],
                "total_earned": int(row["total_earned"] or 0),
                "level": prog["level"],
                "rating_name": prog["rating_name"],
            }
        )
    return out


def _cosmetic_unlocked(item: dict[str, Any], level: int, tier: str, achievements: set[str]) -> bool:
    unlock = item.get("unlock", "level")
    if unlock == "level":
        return level >= int(item.get("min_level") or 1)
    if unlock == "tier":
        need = str(item.get("min_tier") or "lite")
        rank = {"lite": 0, "pro": 1, "max": 2}
        return rank.get(tier, 0) >= rank.get(need, 0)
    if unlock == "achievement":
        return str(item.get("achievement_id") or "") in achievements
    return True


def get_engagement_summary(username: str) -> dict[str, Any]:
    user_id = _username_to_user_id(username)
    if not user_id:
        raise ValueError("用户不存在")
    profile = ensure_profile(user_id)
    progress = sync_xp_from_wallet(user_id)
    stats = _wallet_stats(user_id)
    evaluate_achievements(user_id)

    with get_connection() as conn:
        achievement_rows = conn.execute(
            """
            SELECT achievement_id, unlocked_at FROM user_achievements
            WHERE user_id = ? ORDER BY unlocked_at DESC
            """,
            (user_id,),
        ).fetchall()

    achievements = {r["achievement_id"] for r in achievement_rows}
    ach_list = []
    for aid, meta in ACHIEVEMENTS.items():
        ach_list.append(
            {
                "id": aid,
                "name": meta["name"],
                "desc": meta["desc"],
                "icon": meta["icon"],
                "unlocked": aid in achievements,
                "unlocked_at": next((r["unlocked_at"] for r in achievement_rows if r["achievement_id"] == aid), None),
            }
        )

    backgrounds = [
        {
            "id": bid,
            "name": meta["name"],
            "unlocked": _cosmetic_unlocked(meta, progress["level"], stats["tier"], achievements),
            **{k: v for k, v in meta.items() if k not in ("name",)},
        }
        for bid, meta in BACKGROUNDS.items()
    ]
    themes = [
        {
            "id": tid,
            "name": meta["name"],
            "accent": meta.get("accent", "#c9a96e"),
            "unlocked": _cosmetic_unlocked(meta, progress["level"], stats["tier"], achievements),
        }
        for tid, meta in THEMES.items()
    ]

    season = current_season()
    return {
        "progress": progress,
        "milestones": MILESTONES,
        "achievements": ach_list,
        "backgrounds": backgrounds,
        "themes": themes,
        "profile": {
            "profile_bg": profile.get("profile_bg") or "default",
            "profile_theme": profile.get("profile_theme") or "default",
        },
        "season": season,
        "weekend_double": is_weekend_double(),
        "wheel": wheel_status(username),
        "leaderboard_preview": leaderboard(5),
    }


def update_profile(username: str, *, profile_bg: str | None = None, profile_theme: str | None = None) -> dict[str, Any]:
    user_id = _username_to_user_id(username)
    if not user_id:
        raise ValueError("用户不存在")
    summary = get_engagement_summary(username)
    progress = summary["progress"]
    stats = _wallet_stats(user_id)
    achievements = {a["id"] for a in summary["achievements"] if a["unlocked"]}

    if profile_bg:
        meta = BACKGROUNDS.get(profile_bg)
        if not meta or not _cosmetic_unlocked(meta, progress["level"], stats["tier"], achievements):
            raise ValueError("背景未解锁")
    if profile_theme:
        meta = THEMES.get(profile_theme)
        if not meta or not _cosmetic_unlocked(meta, progress["level"], stats["tier"], achievements):
            raise ValueError("主题未解锁")

    ensure_profile(user_id)
    with get_connection() as conn:
        if profile_bg:
            conn.execute("UPDATE user_gamification SET profile_bg = ? WHERE user_id = ?", (profile_bg, user_id))
        if profile_theme:
            conn.execute("UPDATE user_gamification SET profile_theme = ? WHERE user_id = ?", (profile_theme, user_id))
    return get_engagement_summary(username)
