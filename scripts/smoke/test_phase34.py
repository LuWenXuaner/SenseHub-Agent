#!/usr/bin/env python3
"""Phase 3/4 冒烟：TTS、安全中心、虚拟屏 API、档位门控."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import httpx


def load_env() -> dict[str, str]:
    result: dict[str, str] = {}
    path = ROOT / "config" / "local.env"
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result


def login(client: httpx.Client, password: str) -> None:
    r = client.post("/api/auth/login", json={"username": "admin", "password": password})
    r.raise_for_status()
    token = r.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"


def main() -> int:
    env = load_env()
    host = env.get("API_HOST", "127.0.0.1")
    port = env.get("API_PORT", "8765")
    base = f"http://{host}:{port}"
    password = env.get("ADMIN_PASSWORD", "sensehub")
    tier = env.get("LICENSE_TIER", "lite").lower()

    print(f"Phase 3/4 冒烟 @ {base} (tier={tier})")
    failed = 0

    with httpx.Client(base_url=base, timeout=30.0) as client:
        try:
            client.get("/health").raise_for_status()
        except Exception as exc:
            print(f"FAIL 后端未启动: {exc}")
            return 1

        login(client, password)

        # S01 — 安全中心 API
        r = client.get("/api/security/status")
        if r.status_code == 200:
            data = r.json()
            print(f"OK  S01 安全状态 allow_lan={data.get('allow_lan')}")
        else:
            print(f"FAIL S01 安全状态 {r.status_code}")
            failed += 1

        # T01 — TTS（Pro+）
        r = client.post("/api/tts/speak", json={"text": "冒烟测试"})
        if tier in ("pro", "max"):
            if r.status_code == 200:
                body = r.json()
                print(f"OK  T01 TTS {body.get('url') or body.get('skipped')}")
            else:
                print(f"FAIL T01 TTS {r.status_code} {r.text[:120]}")
                failed += 1
        else:
            if r.status_code == 403:
                print("OK  T01 Lite 档位正确拒绝 TTS")
            else:
                print(f"FAIL T01 Lite 应 403，得 {r.status_code}")
                failed += 1

        # G02 — 虚拟屏校准 API（Max）
        r = client.get("/api/virtual-screen/calibration")
        if tier == "max":
            if r.status_code == 200:
                print(f"OK  G02 校准读取 calibrated={r.json().get('calibrated')}")
            else:
                print(f"FAIL G02 校准 {r.status_code}")
                failed += 1
        else:
            if r.status_code == 403:
                print("OK  G02 非 Max 正确拒绝虚拟屏")
            else:
                print(f"FAIL G02 应 403，得 {r.status_code}")
                failed += 1

        # 多 Agent（Max）
        r = client.post("/api/tasks/multi-agent", json={"text": "截个图"})
        if tier == "max":
            if r.status_code == 200:
                print(f"OK  多Agent 任务 {r.json().get('task_id', '')[:8]}…")
            else:
                print(f"WARN 多Agent {r.status_code}（可能无 LLM Key）")
        else:
            if r.status_code == 403:
                print("OK  多Agent 非 Max 正确拒绝")
            else:
                print(f"FAIL 多Agent 应 403，得 {r.status_code}")
                failed += 1

        # 隧道占位
        r = client.get("/api/tunnel/status")
        if tier == "max":
            if r.status_code == 200:
                print(f"OK  隧道占位 status={r.json().get('status')}")
            else:
                print(f"FAIL 隧道 {r.status_code}")
                failed += 1
        else:
            if r.status_code == 403:
                print("OK  隧道非 Max 拒绝")
            else:
                print(f"FAIL 隧道应 403，得 {r.status_code}")
                failed += 1

    print(f"\nPhase 3/4 完成，失败 {failed} 项")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
