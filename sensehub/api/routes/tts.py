"""TTS 语音反馈 API."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from sensehub.api.deps import get_current_user
from sensehub.feedback.tts import speak
from sensehub.licensing.tier import feature_enabled

router = APIRouter(tags=["tts"])


class TtsRequest(BaseModel):
    text: str
    voice: str | None = None


@router.post("/tts/speak")
async def tts_speak(body: TtsRequest, username: str = Depends(get_current_user)):
    from sensehub.db import wallet as wallet_store

    if not wallet_store.is_plugin_enabled(username, "tts"):
        raise HTTPException(status_code=403, detail="请先在控制台启用语音播报插件")
    if not feature_enabled("tts_feedback", username):
        raise HTTPException(status_code=403, detail="TTS 需要 Pro 档位")
    try:
        result = await speak(body.text, voice=body.voice)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result.get("skipped"):
        return result
    name = Path(result["audio_path"]).name
    result["url"] = f"/api/tts/audio/{name}"
    return result


@router.get("/tts/audio/{filename}")
async def tts_audio(filename: str, _: str = Depends(get_current_user)):
    from sensehub.feedback.tts import _tts_dir

    path = _tts_dir() / filename
    if not path.exists() or ".." in filename:
        raise HTTPException(status_code=404, detail="音频不存在")
    return FileResponse(path, media_type="audio/mpeg")
