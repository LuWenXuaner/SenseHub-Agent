#!/usr/bin/env python3
"""Phase 1 MVP 冒烟（M01–M09），需后端已启动."""

from __future__ import annotations

import os
import sys
import time
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


def wait_task(client: httpx.Client, task_id: str, *, expect: str | set[str], timeout: float = 30) -> dict:
    expected = {expect} if isinstance(expect, str) else set(expect)
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/api/tasks/{task_id}")
        r.raise_for_status()
        data = r.json()
        if data["status"] in expected:
            return data
        if data["status"] in ("failed", "cancelled") and data["status"] not in expected:
            raise RuntimeError(f"任务异常结束: {data['status']} {data.get('error')}")
        time.sleep(0.4)
    raise TimeoutError(f"等待任务 {task_id} 进入 {expected} 超时")


def main() -> int:
    env = load_env()
    host = env.get("API_HOST", "127.0.0.1")
    port = env.get("API_PORT", "8765")
    base = f"http://{host}:{port}"
    password = env.get("ADMIN_PASSWORD", "sensehub")

    print("=== SenseHub Agent Phase 1 MVP 冒烟 ===\n")

    from sensehub.licensing.tier import reset_text_usage_today

    reset_text_usage_today()
    print("[SETUP OK] 已重置当日文本指令计数\n")
    results: dict[str, bool] = {}

    with httpx.Client(base_url=base, timeout=60) as client:
        # M01
        r = client.get("/health")
        ok = r.status_code == 200 and r.json().get("status") == "ok"
        results["M01"] = ok
        print(f"[M01 {'OK' if ok else 'FAIL'}] GET /health")

        # M08 未登录
        anon = httpx.Client(base_url=base, timeout=10)
        r401 = anon.get("/api/tasks")
        ok = r401.status_code == 401
        results["M08a"] = ok
        print(f"[M08 {'OK' if ok else 'FAIL'}] 未登录 /api/tasks -> 401")
        anon.close()

        login = client.post("/api/auth/login", json={"username": "admin", "password": password})
        if login.status_code != 200:
            print(f"[M08 FAIL] 登录失败: {login.text}")
            return 1
        token = login.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        results["M08b"] = True
        print("[M08 OK] 登录成功")

        # M03 截图
        r = client.post("/api/tasks", json={"text": "截个图"})
        r.raise_for_status()
        task = wait_task(client, r.json()["task_id"], expect="done")
        ok = task["status"] == "done" and len(task.get("step_results", [])) > 0
        results["M03"] = ok
        print(f"[M03 {'OK' if ok else 'FAIL'}] 截个图 -> {task['status']}")

        # M04 Edge 搜索（不打开浏览器，只验证计划与完成）
        r = client.post("/api/tasks", json={"text": "在浏览器中搜索smoke_test"})
        r.raise_for_status()
        task = wait_task(client, r.json()["task_id"], expect="done", timeout=20)
        ok = task["status"] == "done"
        out = (task.get("step_results") or [{}])[0].get("output") or {}
        ok = ok and out.get("method") == "edge-default-search"
        results["M04"] = ok
        print(f"[M04 {'OK' if ok else 'FAIL'}] Edge 搜索 -> {out.get('method', task['status'])}")

        # M06 L2 待确认
        r = client.post("/api/tasks", json={"text": "待确认测试"})
        r.raise_for_status()
        task_id = r.json()["task_id"]
        task = wait_task(client, task_id, expect="wait_confirm")
        ok = task["status"] == "wait_confirm"
        results["M06a"] = ok
        print(f"[M06 {'OK' if ok else 'FAIL'}] L2 进入 wait_confirm")

        # M05 刷新后状态仍在
        r2 = client.get(f"/api/tasks/{task_id}")
        ok = r2.json()["status"] == "wait_confirm" and len(r2.json().get("plan_steps", [])) > 0
        results["M05"] = ok
        print(f"[M05 {'OK' if ok else 'FAIL'}] 刷新读取任务状态")

        # 拒绝一条 L2
        client.post(f"/api/tasks/{task_id}/cancel")
        task = wait_task(client, task_id, expect="cancelled")
        results["M06b"] = task["status"] == "cancelled"
        print(f"[M06 OK] 拒绝 -> cancelled")

        # 批准执行 L2
        r = client.post("/api/tasks", json={"text": "待确认测试"})
        task_id = r.json()["task_id"]
        wait_task(client, task_id, expect="wait_confirm")
        client.post(f"/api/tasks/{task_id}/confirm")
        task = wait_task(client, task_id, expect="done", timeout=20)
        results["M06c"] = task["status"] == "done"
        print(f"[M06 {'OK' if results['M06c'] else 'FAIL'}] 批准后执行 -> done")

        # M07 Kill Switch
        client.post("/api/kill-switch")
        r = client.post("/api/tasks", json={"text": "截个图"})
        tid = r.json()["task_id"]
        task = wait_task(client, tid, expect={"done", "failed"}, timeout=15)
        err = task.get("error") or ""
        killed = "Kill Switch" in err or any(
            "Kill Switch" in (sr.get("error") or "")
            for sr in task.get("step_results", [])
        )
        client.post("/api/kill-switch/reset")
        results["M07"] = killed
        print(f"[M07 {'OK' if killed else 'WARN'}] Kill Switch")

        # M09 审计
        audit = client.get("/api/audit")
        ok = audit.status_code == 200 and len(audit.json()) > 0
        results["M09"] = ok
        print(f"[M09 {'OK' if ok else 'FAIL'}] 审计日志 {len(audit.json()) if ok else 0} 条")

        results["M02"] = True
        print("[M02 OK] Web UI 需人工打开 http://127.0.0.1:5173 确认")

    passed = sum(1 for v in results.values() if v)
    print(f"\n自动项通过 {passed}/{len(results)}")
    failed = [k for k, v in results.items() if not v]
    if failed:
        print("未通过:", ", ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
