#!/usr/bin/env python3
"""感知模块测试 — 已合并到 test_env.py（E06–E11）."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    script = ROOT / "scripts" / "smoke" / "test_env.py"
    print("转发至 test_env.py（E06–E11）...\n")
    return subprocess.call([sys.executable, str(script)])


if __name__ == "__main__":
    raise SystemExit(main())
