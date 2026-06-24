#!/usr/bin/env python3
"""Phase 0 环境验收（E01–E15）+ Phase 2 前置感知检查（E06–E11）."""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def load_env() -> dict[str, str]:
    env_path = ROOT / "config" / "local.env"
    result: dict[str, str] = {}
    if not env_path.exists():
        print(f"[E03 FAIL] 缺少 {env_path}")
        return result
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result


def load_paths() -> dict:
    path = ROOT / "config" / "paths.yaml"
    if not path.exists():
        return {}
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def resolve_python(env: dict[str, str]) -> Path | None:
    py_path = env.get("PYTHON_PATH", "").strip()
    if py_path:
        p = Path(py_path)
        if p.exists():
            return p
    venv = env.get("VENV_PATH", "").strip()
    if venv:
        p = Path(venv) / "Scripts" / "python.exe"
        if p.exists():
            return p
    return Path(sys.executable)


def check_e01(env: dict[str, str]) -> bool:
    py = resolve_python(env)
    if not py:
        print("[E01 FAIL] 请设置 PYTHON_PATH")
        return False
    r = subprocess.run([str(py), "--version"], capture_output=True, text=True)
    ok = r.returncode == 0 and "3.1" in (r.stdout + r.stderr)
    print(f"[E01 {'OK' if ok else 'FAIL'}] {py} -> {(r.stdout or r.stderr).strip()}")
    return ok


def check_e02(env: dict[str, str]) -> bool:
    node = env.get("NODE_PATH", "").strip() or "node"
    r = subprocess.run([node, "--version"], capture_output=True, text=True)
    ok = r.returncode == 0 and "v" in (r.stdout + r.stderr)
    print(f"[E02 {'OK' if ok else 'FAIL'}] Node -> {(r.stdout or r.stderr).strip()}")
    return ok


def check_e03(env: dict[str, str]) -> bool:
    paths = ROOT / "config" / "paths.yaml"
    local = ROOT / "config" / "local.env"
    required = ["PYTHON_PATH", "DATA_ROOT", "MODELS_ROOT"]
    missing = [k for k in required if not env.get(k, "").strip()]
    ok = paths.exists() and local.exists() and not missing
    print(f"[E03 {'OK' if ok else 'FAIL'}] 配置文件" + (f" 缺少 {missing}" if missing else ""))
    return ok


def check_e04(env: dict[str, str]) -> bool:
    data = Path(env.get("DATA_ROOT", ""))
    try:
        data.mkdir(parents=True, exist_ok=True)
        test = data / ".write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        print(f"[E04 OK] {data} 可写")
        return True
    except OSError as exc:
        print(f"[E04 FAIL] {exc}")
        return False


def check_e05(env: dict[str, str]) -> bool:
    if env.get("USE_CUDA", "").lower() not in ("1", "true", "yes"):
        print("[E05 SKIP] USE_CUDA 未启用")
        return True
    try:
        import torch

        ok = torch.cuda.is_available()
        print(f"[E05 {'OK' if ok else 'WARN'}] CUDA available={ok}")
        return True
    except ImportError:
        print("[E05 WARN] 未安装 torch，跳过 GPU 检查")
        return True


def check_e08(env: dict[str, str], paths: dict) -> bool:
    import shutil

    ffmpeg = env.get("FFMPEG_PATH") or paths.get("tools", {}).get("ffmpeg") or shutil.which("ffmpeg")
    if not ffmpeg:
        print("[E08 FAIL] 未找到 FFmpeg")
        return False
    r = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True)
    ok = r.returncode == 0
    print(f"[E08 {'OK' if ok else 'FAIL'}] FFmpeg")
    return ok


def check_e14(env: dict[str, str]) -> bool:
    db_path = Path(env.get("SQLITE_PATH", "")) or Path(env.get("DATA_ROOT", "")) / "db" / "sensehub.db"
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS _smoke (id INTEGER PRIMARY KEY, v TEXT)")
            conn.execute("INSERT INTO _smoke (v) VALUES ('ok')")
            row = conn.execute("SELECT v FROM _smoke ORDER BY id DESC LIMIT 1").fetchone()
            conn.execute("DROP TABLE _smoke")
        ok = row and row[0] == "ok"
        print(f"[E14 {'OK' if ok else 'FAIL'}] SQLite {db_path}")
        return ok
    except sqlite3.Error as exc:
        print(f"[E14 FAIL] {exc}")
        return False


def check_e06(paths: dict, env: dict[str, str]) -> bool:
    if importlib.util.find_spec("cv2") is None:
        print("[E06 FAIL] 未安装 opencv-python")
        return False
    import cv2

    index = int(paths.get("devices", {}).get("camera_index", env.get("CAMERA_INDEX", 0)))
    cap = cv2.VideoCapture(index)
    ok, frame = cap.read()
    cap.release()
    ok = ok and frame is not None and frame.size > 0
    print(f"[E06 {'OK' if ok else 'FAIL'}] 摄像头 index={index}")
    return ok


def check_e07(paths: dict, env: dict[str, str]) -> bool:
    if importlib.util.find_spec("sounddevice") is None:
        print("[E07 FAIL] 未安装 sounddevice")
        return False
    import sounddevice as sd
    import numpy as np

    duration = 1.0
    sample_rate = 16000
    try:
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
        sd.wait()
        out_dir = Path(paths.get("data", {}).get("recordings", "")) or Path(env.get("DATA_ROOT", "")) / "recordings"
        out_dir.mkdir(parents=True, exist_ok=True)
        wav_path = out_dir / "_smoke_mic.wav"
        with wave.open(str(wav_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
        ok = wav_path.stat().st_size > 1000 and np.abs(audio).max() >= 0
        print(f"[E07 {'OK' if ok else 'FAIL'}] 麦克风录音 -> {wav_path.name}")
        wav_path.unlink(missing_ok=True)
        return ok
    except Exception as exc:
        print(f"[E07 FAIL] {exc}")
        return False


def check_e10(paths: dict) -> bool:
    weights = Path(paths.get("models", {}).get("yolo_weights", ""))
    if not weights.exists():
        print(f"[E10 FAIL] YOLO 权重不存在: {weights}")
        return False
    if importlib.util.find_spec("ultralytics") is None:
        print("[E10 FAIL] 未安装 ultralytics")
        return False
    from ultralytics import YOLO

    model = YOLO(str(weights))
    import numpy as np

    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    results = model.predict(dummy, verbose=False)
    ok = results is not None
    print(f"[E10 {'OK' if ok else 'FAIL'}] YOLO 推理 {weights.name}")
    return ok


def check_e11(paths: dict) -> bool:
    whisper_path = Path(paths.get("models", {}).get("whisper_model", ""))
    if not whisper_path.exists():
        print(f"[E11 FAIL] Whisper 模型不存在: {whisper_path}")
        return False
    if importlib.util.find_spec("faster_whisper") is None:
        print(f"[E11 WARN] faster-whisper 未安装，模型已就绪: {whisper_path.name}")
        print("         Phase 2 前请: pip install faster-whisper")
        return True
    print(f"[E11 OK] Whisper 模型 + faster-whisper 已安装")
    return True


def main() -> int:
    print("=== SenseHub Agent 环境与感知验收 ===\n")
    env = load_env()
    paths = load_paths()
    checks = [
        ("E03", lambda: check_e03(env)),
        ("E01", lambda: check_e01(env)),
        ("E02", lambda: check_e02(env)),
        ("E04", lambda: check_e04(env)),
        ("E05", lambda: check_e05(env)),
        ("E08", lambda: check_e08(env, paths)),
        ("E14", lambda: check_e14(env)),
        ("E06", lambda: check_e06(paths, env)),
        ("E07", lambda: check_e07(paths, env)),
        ("E10", lambda: check_e10(paths)),
        ("E11", lambda: check_e11(paths)),
    ]
    results = {name: fn() for name, fn in checks}
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n通过 {passed}/{total}")
    for name, ok in results.items():
        if not ok:
            print(f"  未通过: {name}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
