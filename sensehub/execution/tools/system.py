"""系统信息、通知、受控命令."""

from __future__ import annotations

import subprocess
from datetime import datetime
from typing import Any


def get_datetime(params: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now()
    weekdays = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
    return {
        "iso": now.isoformat(timespec="seconds"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": weekdays[now.weekday()],
    }


def notify(params: dict[str, Any]) -> dict[str, Any]:
    title = str(params.get("title", "灵枢 Agent"))
    message = str(params.get("message", ""))
    if not message:
        raise ValueError("message 不能为空")
    safe_title = title.replace("'", "''")
    safe_msg = message.replace("'", "''")
    ps = (
        f"Add-Type -AssemblyName System.Windows.Forms; "
        f"[System.Windows.Forms.MessageBox]::Show('{safe_msg}', '{safe_title}')"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return {"title": title, "message": message, "method": "messagebox"}


_ALLOWED_COMMANDS = frozenset(
    {
        "dir",
        "echo",
        "where",
        "tasklist",
        "systeminfo",
        "ipconfig",
        "ping",
    }
)


def run_command(params: dict[str, Any]) -> dict[str, Any]:
    command = str(params.get("command", "")).strip()
    if not command:
        raise ValueError("command 不能为空")
    base = command.split()[0].lower()
    if base not in _ALLOWED_COMMANDS:
        raise PermissionError(f"命令不在白名单: {base}")
    proc = subprocess.run(
        command,
        shell=bool(params.get("shell", True)),
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": command,
        "exit_code": proc.returncode,
        "stdout": (proc.stdout or "")[:8000],
        "stderr": (proc.stderr or "")[:2000],
    }
