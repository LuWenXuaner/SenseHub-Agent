"""微信发消息全链路诊断（与 Hub /api/hub/command 同路径）.

用法（项目根目录）:
  D:\\anaconda3\\envs\\py312\\python.exe scripts/diag_wechat_flow.py

流程:
  1. 重置 Kill Switch，订阅 agent 事件并打印时间线
  2. 走 process_user_input（原子捷径 + run_plan_agent）
  3. 当你在微信里确认消息已发出后，回到终端按【回车】标记人感知完成时刻
  4. 写出 SenseHubData/diag_wechat_report.json
"""
from __future__ import annotations

import asyncio
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sensehub.cognition.dispatch import process_user_input
from sensehub.cognition.quick_match import match_atomic_plan
from sensehub.execution.kill_switch import is_killed, reset as reset_kill_switch
from sensehub.gateway import events as agent_events

TEXT = "打开微信，给文件传输助手发送你好"
REPORT = ROOT / "SenseHubData" / "diag_wechat_report.json"

_t0 = time.perf_counter()
_events: list[dict] = []
_human_ms: int | None = None
_marker_ready = threading.Event()
_wechat_started = threading.Event()


def _rel_ms() -> int:
    return int((time.perf_counter() - _t0) * 1000)


def _on_event(ev: dict) -> None:
    entry = {"t_ms": _rel_ms(), **ev}
    _events.append(entry)
    typ = ev.get("type", "")
    tool = ev.get("tool", "")
    ok = ev.get("success")
    extra = ""
    if typ == "tool_end":
        extra = f" success={ok} error={ev.get('error') or ''}"
    elif typ == "phase":
        extra = f" phase={ev.get('phase')} status={ev.get('status')}"
    print(f"[{_rel_ms():6d}ms] {typ} {tool}{extra}")
    if typ == "tool_start" and tool == "wechat_send_message":
        _wechat_started.set()
        _marker_ready.set()


def _human_marker_thread() -> None:
    global _human_ms
    _marker_ready.wait(timeout=120)
    if not _marker_ready.is_set():
        return
    print()
    print("=" * 64)
    print("【人工确认】请在微信里确认消息已发送（或确认已失败）后，按回车继续…")
    print("=" * 64)
    try:
        input()
    except EOFError:
        return
    _human_ms = _rel_ms()
    print(f"已记录人工确认时刻: {_human_ms}ms")


async def _run_dispatch() -> dict:
    return await process_user_input(TEXT, source="diag", user_id="diag")


def main() -> None:
    reset_kill_switch()
    plan = match_atomic_plan(TEXT)
    print(f"指令: {TEXT}")
    print(f"原子捷径: {'命中 — ' + plan.summary if plan else '未命中'}")
    if plan:
        print(f"计划参数: {plan.steps[0].params}")
    print(f"Kill Switch: {'激活' if is_killed() else '未激活'}")
    print()

    agent_events.subscribe(_on_event)
    marker = threading.Thread(target=_human_marker_thread, daemon=True)
    marker.start()

    backend_ms = 0
    result: dict = {}
    error: str | None = None
    try:
        t_dispatch = time.perf_counter()
        result = asyncio.run(_run_dispatch())
        backend_ms = int((time.perf_counter() - t_dispatch) * 1000)
    except Exception as exc:
        error = str(exc)
        _marker_ready.set()
    finally:
        agent_events.unsubscribe(_on_event)

    marker.join(timeout=300)

    step_results = result.get("step_results") or []
    wechat_out = None
    wechat_ok = None
    wechat_err = None
    wechat_dur = None
    for r in step_results:
        out = (getattr(r, "output", None) or {}) if not isinstance(r, dict) else (r.get("output") or {})
        if isinstance(out, dict) and (out.get("contact") or out.get("method") == "ctrl_f_search_paste_send"):
            wechat_out = out
            wechat_ok = getattr(r, "success", r.get("success") if isinstance(r, dict) else None)
            wechat_err = getattr(r, "error", r.get("error") if isinstance(r, dict) else None)
            wechat_dur = getattr(r, "duration_ms", r.get("duration_ms") if isinstance(r, dict) else None)
            break

    report = {
        "text": TEXT,
        "atomic_plan": plan.summary if plan else None,
        "backend_total_ms": backend_ms,
        "human_confirm_ms": _human_ms,
        "human_minus_backend_ms": (_human_ms - backend_ms) if _human_ms is not None else None,
        "executed": result.get("executed"),
        "reply": result.get("reply"),
        "error": error,
        "kill_switch_at_end": is_killed(),
        "wechat_step": {
            "success": wechat_ok,
            "error": wechat_err,
            "output": wechat_out,
            "duration_ms": wechat_dur,
        },
        "events": _events,
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print()
    print("--- 摘要 ---")
    print(f"  后端总耗时: {backend_ms} ms")
    if _human_ms is not None:
        print(f"  人工确认时刻: {_human_ms} ms (差值 {_human_ms - backend_ms} ms)")
    print(f"  执行结果: {report['reply'] or report['error'] or '无'}")
    print(f"  微信步骤: success={report['wechat_step']['success']} error={report['wechat_step']['error']}")
    print(f"  报告: {REPORT}")


if __name__ == "__main__":
    main()
