"""局域网访问与白名单（Phase 3）."""

from __future__ import annotations

import ipaddress
import json

from sensehub.db.database import get_connection
from sensehub.settings import get_settings


def _load_policies() -> dict:
    return get_settings().policies


def allow_lan_enabled() -> bool:
    net = _load_policies().get("network", {})
    return bool(net.get("allow_lan", False))


def get_ip_whitelist() -> list[str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM security_settings WHERE key = 'ip_whitelist'"
        ).fetchone()
    if row:
        return json.loads(row["value"] or "[]")
    net = _load_policies().get("network", {})
    return list(net.get("ip_whitelist") or [])


def set_ip_whitelist(ips: list[str]) -> list[str]:
    cleaned = [ip.strip() for ip in ips if ip.strip()]
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO security_settings (key, value) VALUES ('ip_whitelist', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (json.dumps(cleaned, ensure_ascii=False),),
        )
    return cleaned


def is_client_allowed(client_host: str | None) -> bool:
    if not client_host:
        return False
    host = client_host.strip()
    if host in ("127.0.0.1", "::1", "localhost"):
        return True
    if not allow_lan_enabled():
        return False
    whitelist = get_ip_whitelist()
    if not whitelist:
        # 局域网模式但未配白名单：允许 RFC1918 私有网段
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_private
        except ValueError:
            return False
    if host in whitelist:
        return True
    try:
        ip = ipaddress.ip_address(host)
        for entry in whitelist:
            if "/" in entry:
                if ip in ipaddress.ip_network(entry, strict=False):
                    return True
            elif host == entry:
                return True
    except ValueError:
        pass
    return False
