"""Edge TTS 语音反馈（Phase 3）."""

from __future__ import annotations

import uuid
from pathlib import Path

from sensehub.settings import get_settings


def _tts_dir() -> Path:
    settings = get_settings()
    base = Path(settings.data_root) if settings.data_root else Path(settings.screenshots_dir).parent
    p = base / "tts"
    p.mkdir(parents=True, exist_ok=True)
    return p


async def speak(text: str, *, voice: str | None = None) -> dict[str, str]:
    if not text.strip():
        raise ValueError("播报文本不能为空")
    settings = get_settings()
    if not settings.tts_enabled:
        return {"skipped": "true", "reason": "TTS 未启用"}
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("请安装 edge-tts: pip install edge-tts") from exc

    voice_name = voice or settings.tts_voice or "zh-CN-XiaoxiaoNeural"
    out = _tts_dir() / f"tts_{uuid.uuid4().hex[:12]}.mp3"
    communicate = edge_tts.Communicate(text.strip(), voice_name)
    await communicate.save(str(out))
    return {"audio_path": str(out), "voice": voice_name, "text": text.strip()}


def speak_sync(text: str) -> dict[str, str]:
    import asyncio

    return asyncio.run(speak(text))
