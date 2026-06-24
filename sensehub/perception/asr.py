"""语音识别（faster-whisper + FFmpeg 转码）."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from sensehub.settings import get_settings

_model = None
_model_lock = __import__("threading").Lock()


def _resolve_model_size() -> str:
    settings = get_settings()
    whisper_path = Path(settings.paths.get("models", {}).get("whisper_model", ""))
    if whisper_path.name.startswith("ggml-"):
        return whisper_path.name.replace("ggml-", "").replace(".bin", "")
    if whisper_path.exists():
        return str(whisper_path.parent)
    return "small"


def _ffmpeg_path() -> str:
    settings = get_settings()
    custom = settings.paths.get("tools", {}).get("ffmpeg", "") or settings.ffmpeg_path
    if custom and Path(custom).exists():
        return str(custom)
    found = shutil.which("ffmpeg")
    if not found:
        raise ValueError("未找到 FFmpeg，请在 config/local.env 设置 FFMPEG_PATH")
    return found


def _to_wav(src: Path) -> Path:
    """浏览器 MediaRecorder 多为 webm，Whisper 需要 wav/pcm。"""
    if src.suffix.lower() == ".wav":
        return src
    dst = src.with_suffix(".wav")
    ffmpeg = _ffmpeg_path()
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(src),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(dst),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not dst.exists():
        err = (proc.stderr or proc.stdout or "").strip()[-400:]
        raise ValueError(f"音频转码失败，请确认 FFmpeg 可用: {err}")
    return dst


def _get_model():
    global _model
    with _model_lock:
        if _model is not None:
            return _model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "未安装 faster-whisper，请执行: pip install faster-whisper"
            ) from exc
        settings = get_settings()
        device = "cuda" if settings.use_cuda else "cpu"
        compute = "float16" if device == "cuda" else "int8"
        model_ref = _resolve_model_size()
        try:
            _model = WhisperModel(model_ref, device=device, compute_type=compute)
        except Exception:
            _model = WhisperModel("small", device="cpu", compute_type="int8")
        return _model


def transcribe_file(path: Path, *, language: str = "zh") -> tuple[str, int]:
    start = time.perf_counter()
    wav_path = _to_wav(path)
    cleanup = wav_path if wav_path != path else None
    try:
        model = _get_model()
        segments, _ = model.transcribe(
            str(wav_path),
            language=language,
            beam_size=3,
            best_of=3,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt="灵枢打开虚拟屏。灵枢打开记事本。灵枢截个图。灵枢关闭虚拟屏。",
        )
        text = "".join(seg.text for seg in segments).strip()
        duration_ms = int((time.perf_counter() - start) * 1000)
        return text, duration_ms
    finally:
        if cleanup and cleanup.exists():
            cleanup.unlink(missing_ok=True)


def transcribe_bytes(data: bytes, *, suffix: str = ".wav") -> tuple[str, int]:
    if not data or len(data) < 64:
        raise ValueError("音频太短或为空，请至少说 1～2 秒")
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        return transcribe_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
