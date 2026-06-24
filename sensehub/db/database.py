"""SQLite 初始化与连接."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from sensehub.settings import get_settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    intent_text TEXT NOT NULL,
    summary TEXT DEFAULT '',
    plan_json TEXT DEFAULT '[]',
    current_step INTEGER DEFAULT 0,
    results_json TEXT DEFAULT '[]',
    error TEXT,
    trace_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    user_label TEXT DEFAULT 'local',
    input_text TEXT,
    action TEXT,
    risk_level TEXT,
    result TEXT,
    trace_id TEXT
);

CREATE TABLE IF NOT EXISTS usage_daily (
    day TEXT NOT NULL,
    metric TEXT NOT NULL,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (day, metric)
);

CREATE TABLE IF NOT EXISTS rules (
    rule_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    tier_min TEXT DEFAULT 'lite',
    trigger_json TEXT NOT NULL,
    action_json TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS perception_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    rule_id TEXT,
    message TEXT,
    payload_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS virtual_screen_calibration (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    points_json TEXT NOT NULL DEFAULT '{}',
    matrix_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS security_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT DEFAULT '',
    email TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS email_verification_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    code TEXT NOT NULL,
    purpose TEXT NOT NULL DEFAULT 'register',
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS oauth_identities (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    provider_user_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(provider, provider_user_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'local',
    title TEXT NOT NULL DEFAULT '新会话',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    task_id TEXT,
    meta_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);

CREATE TABLE IF NOT EXISTS user_wallets (
    user_id TEXT PRIMARY KEY,
    public_id TEXT UNIQUE NOT NULL,
    invite_code TEXT UNIQUE NOT NULL,
    points_balance INTEGER DEFAULT 0,
    total_earned INTEGER DEFAULT 0,
    total_spent INTEGER DEFAULT 0,
    last_checkin_date TEXT,
    checkin_streak INTEGER DEFAULT 0,
    invited_by_user_id TEXT,
    tier TEXT DEFAULT 'lite',
    tier_expires_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS points_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    delta INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    entry_type TEXT NOT NULL,
    note TEXT DEFAULT '',
    ref_id TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_points_ledger_user ON points_ledger(user_id, id DESC);

CREATE TABLE IF NOT EXISTS exchange_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    item_label TEXT NOT NULL,
    cost INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS invite_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inviter_user_id TEXT NOT NULL,
    invitee_user_id TEXT,
    invite_code TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    registered_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS usage_bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    bill_date TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    unit TEXT DEFAULT '',
    points_cost INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_plugins (
    user_id TEXT NOT NULL,
    plugin_id TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, plugin_id)
);

CREATE TABLE IF NOT EXISTS llm_token_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    day TEXT NOT NULL,
    role TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    request_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, day, role, provider, model)
);

CREATE INDEX IF NOT EXISTS idx_llm_token_usage_user_day ON llm_token_usage(user_id, day);
"""


def get_db_path() -> Path:
    settings = get_settings()
    path = Path(settings.sqlite_path) if settings.sqlite_path else Path(settings.data_root) / "db" / "sensehub.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db() -> None:
    path = get_db_path()
    with sqlite3.connect(path) as conn:
        conn.executescript(_SCHEMA)
        _migrate(conn)
        conn.commit()
    backfill_all_wallets()


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "email" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL"
    )
    task_cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    if "session_id" not in task_cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN session_id TEXT")
    sess_cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    if "channel" not in sess_cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN channel TEXT NOT NULL DEFAULT 'hub'")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS user_gamification (
            user_id TEXT PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            profile_bg TEXT DEFAULT 'default',
            profile_theme TEXT DEFAULT 'default',
            milestone_claimed_json TEXT DEFAULT '[]',
            weekend_checkins INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id TEXT NOT NULL,
            achievement_id TEXT NOT NULL,
            unlocked_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, achievement_id)
        );
        CREATE TABLE IF NOT EXISTS wheel_spins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            prize_id TEXT NOT NULL,
            prize_label TEXT NOT NULL,
            points_won INTEGER NOT NULL DEFAULT 0,
            cost INTEGER NOT NULL DEFAULT 0,
            spin_date TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_wheel_spins_user_day ON wheel_spins(user_id, spin_date);
        """
    )
    _seed_admin_if_empty(conn)


def _seed_admin_if_empty(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    if not row or int(row[0]) > 0:
        return
    from sensehub.security.auth import hash_password

    user_id = str(__import__("uuid").uuid4())
    conn.execute(
        """
        INSERT INTO users (user_id, username, password_hash, display_name, email)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, "admin", hash_password("123456"), "管理员", None),
    )


ADMIN_SEED_POINTS = 100_000


def backfill_all_wallets() -> None:
    from sensehub.db.wallet import ensure_wallet

    with get_connection() as conn:
        rows = conn.execute("SELECT user_id, username FROM users").fetchall()
    for row in rows:
        ensure_wallet(row["user_id"])
    with get_connection() as conn:
        admin = conn.execute("SELECT user_id FROM users WHERE username = 'admin'").fetchone()
        if admin:
            wallet = conn.execute(
                "SELECT points_balance, total_earned FROM user_wallets WHERE user_id = ?",
                (admin["user_id"],),
            ).fetchone()
            if wallet and int(wallet["points_balance"]) < ADMIN_SEED_POINTS:
                conn.execute(
                    """
                    UPDATE user_wallets
                    SET points_balance = ?, total_earned = MAX(total_earned, ?)
                    WHERE user_id = ?
                    """,
                    (ADMIN_SEED_POINTS, ADMIN_SEED_POINTS, admin["user_id"]),
                )


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
