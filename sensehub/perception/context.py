"""感知上下文：供 Agent 注入与工具查询."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any


class PerceptionContext:
    _instance: PerceptionContext | None = None

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: dict[str, Any] = {
            "person_count": 0,
            "gesture": {"type": "none", "confidence": 0.0, "description": ""},
            "intent": {"primary": "no_activity", "description": ""},
            "detections": [],
            "updated_at": 0.0,
        }
        self._recent: deque[dict[str, Any]] = deque(maxlen=40)
        self._last_logged: dict[str, float] = {}

    @classmethod
    def get(cls) -> PerceptionContext:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def update(self, payload: dict[str, Any]) -> None:
        now = time.time()
        gesture = payload.get("gesture") or {}
        gtype = str(gesture.get("type") or "none")
        with self._lock:
            self._snapshot = {
                "person_count": int(payload.get("person_count") or 0),
                "gesture": gesture,
                "intent": payload.get("intent") or {},
                "detections": payload.get("detections") or [],
                "updated_at": now,
            }
            if gtype != "none":
                last = self._last_logged.get(gtype, 0.0)
                if now - last >= 2.0:
                    self._last_logged[gtype] = now
                    self._recent.append(
                        {
                            "type": gtype,
                            "confidence": float(gesture.get("confidence") or 0),
                            "description": gesture.get("description") or gtype,
                            "at": now,
                        }
                    )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._snapshot)

    def recent_events(self, *, within_sec: float = 30.0) -> list[dict[str, Any]]:
        cutoff = time.time() - within_sec
        with self._lock:
            return [e for e in list(self._recent) if float(e.get("at") or 0) >= cutoff]

    def prompt_addon(self) -> str:
        snap = self.snapshot()
        if not snap.get("updated_at"):
            return ""
        age = time.time() - float(snap["updated_at"])
        if age > 120:
            return ""
        lines = ["【感知上下文】摄像头开启时的环境摘要（仅供参考，以用户文字指令为准）："]
        pc = int(snap.get("person_count") or 0)
        lines.append(f"- 画面人数：{pc}")
        g = snap.get("gesture") or {}
        if g.get("type") and g.get("type") != "none":
            lines.append(
                f"- 当前手势：{g.get('description') or g.get('type')}（置信度 {float(g.get('confidence') or 0):.2f}）"
            )
        for ev in self.recent_events(within_sec=15.0)[-3:]:
            sec = max(0, int(time.time() - float(ev.get("at") or 0)))
            lines.append(f"- 约 {sec} 秒前：{ev.get('description') or ev.get('type')}")
        intent = snap.get("intent") or {}
        if intent.get("description"):
            lines.append(f"- 意图提示：{intent['description']}")
        lines.append("- 除非用户已配置手势规则，否则不要仅因点头/摇头自动确认或取消任务。")
        return "\n".join(lines)

    def to_tool_output(self) -> dict[str, Any]:
        return {
            "snapshot": self.snapshot(),
            "recent_events": self.recent_events(within_sec=30.0),
        }
