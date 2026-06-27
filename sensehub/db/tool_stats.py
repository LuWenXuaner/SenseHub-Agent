"""工具调用统计（热力与成功率）."""

from __future__ import annotations

from datetime import date

from sensehub.db.database import get_connection

_DEFAULT_SHORTCUTS: list[dict[str, str]] = [
    {"tool": "notepad_type_save", "label": "记事本", "command": "打开记事本输入 Hello 并保存"},
    {"tool": "wechat_send_message", "label": "微信", "command": "给文件传输助手发消息：你好"},
    {"tool": "browser_navigate", "label": "浏览器", "command": "打开浏览器搜索 SenseHub Agent"},
    {"tool": "get_weather", "label": "天气", "command": "查询北京天气"},
]

_SHORTCUT_BY_TOOL: dict[str, dict[str, str]] = {
    "notepad_type_save": {"label": "记事本", "command": "打开记事本输入 Hello 并保存"},
    "wechat_send_message": {"label": "微信", "command": "给文件传输助手发消息：你好"},
    "browser_navigate": {"label": "浏览器", "command": "打开浏览器搜索 SenseHub Agent"},
    "web_search": {"label": "搜索", "command": "搜索人工智能最新进展"},
    "get_weather": {"label": "天气", "command": "查询北京天气"},
    "generate_document": {"label": "文档", "command": "生成一份项目周报 Word 文档"},
    "screenshot": {"label": "截图", "command": "截取当前屏幕"},
    "open_app": {"label": "打开应用", "command": "打开记事本"},
}


def record_tool_call(*, tool: str, success: bool, duration_ms: int = 0) -> None:
    if not tool:
        return
    day = date.today().isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT calls, success, total_ms FROM tool_stats WHERE tool = ? AND day = ?",
            (tool, day),
        ).fetchone()
        if row:
            conn.execute(
                """
                UPDATE tool_stats
                SET calls = calls + 1,
                    success = success + ?,
                    total_ms = total_ms + ?
                WHERE tool = ? AND day = ?
                """,
                (1 if success else 0, max(0, duration_ms), tool, day),
            )
        else:
            conn.execute(
                """
                INSERT INTO tool_stats (tool, day, calls, success, total_ms)
                VALUES (?, ?, 1, ?, ?)
                """,
                (tool, day, 1 if success else 0, max(0, duration_ms)),
            )


def tool_insights(*, days: int = 7, limit: int = 8) -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT tool,
                   SUM(calls) AS calls,
                   SUM(success) AS success,
                   SUM(total_ms) AS total_ms
            FROM tool_stats
            WHERE day >= date('now', ?)
            GROUP BY tool
            ORDER BY calls DESC
            LIMIT ?
            """,
            (f"-{max(1, days)} days", limit),
        ).fetchall()

    top_tools = []
    for r in rows:
        calls = int(r["calls"] or 0)
        success = int(r["success"] or 0)
        total_ms = int(r["total_ms"] or 0)
        top_tools.append(
            {
                "tool": r["tool"],
                "calls": calls,
                "success_rate": round(success / calls, 3) if calls else 0,
                "avg_ms": int(total_ms / calls) if calls else 0,
            }
        )

    shortcuts: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in top_tools:
        tool = str(item["tool"])
        meta = _SHORTCUT_BY_TOOL.get(tool)
        if meta and tool not in seen:
            shortcuts.append({"tool": tool, **meta})
            seen.add(tool)
    for fallback in _DEFAULT_SHORTCUTS:
        if len(shortcuts) >= 4:
            break
        if fallback["tool"] not in seen:
            shortcuts.append(fallback)
            seen.add(fallback["tool"])

    return {"top_tools": top_tools, "suggested_shortcuts": shortcuts[:6]}
