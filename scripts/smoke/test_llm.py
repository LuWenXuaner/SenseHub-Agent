#!/usr/bin/env python3
"""LLM API 连通测试（E12–E13 骨架）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    env_path = ROOT / "config" / "local.env"
    models_path = ROOT / "config" / "models.yaml"

    if not env_path.exists():
        print("[E12 FAIL] 缺少 config/local.env")
        return 1
    if not models_path.exists():
        print("[E13 FAIL] 缺少 config/models.yaml")
        return 1

    keys_found = []
    for line in env_path.read_text(encoding="utf-8").splitlines():
        for name in ("SILICONFLOW_API_KEY", "VOLCENGINE_API_KEY"):
            if line.startswith(f"{name}=") and line.split("=", 1)[1].strip():
                keys_found.append(name)
    if len(keys_found) < 2:
        missing = {"SILICONFLOW_API_KEY", "VOLCENGINE_API_KEY"} - set(keys_found)
        print(f"[E12 FAIL] local.env 缺少 API Key: {', '.join(sorted(missing))}")
        return 1

    print(f"[E12 OK] 已配置: {', '.join(keys_found)}（完整调用测试于 Phase 1 实现）")
    print("[E13 OK] models.yaml 存在（路由测试于 Phase 1 实现）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
