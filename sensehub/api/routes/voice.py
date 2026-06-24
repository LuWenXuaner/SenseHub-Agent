"""语音转写与大脑分流（问答 / 执行）."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from sensehub.api.deps import get_current_user
from sensehub.models.perception_schemas import VoiceCommandResponse, VoiceTranscribeResponse
from sensehub.models.schemas import TaskCreate
from sensehub.rules.engine import run_voice_command

router = APIRouter(tags=["voice"])


@router.post("/voice/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe(
    _: str = Depends(get_current_user),
    audio: UploadFile = File(...),
):
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="音频为空")
    suffix = ".wav"
    if audio.filename and "." in audio.filename:
        suffix = "." + audio.filename.rsplit(".", 1)[-1].lower()
    try:
        from sensehub.perception.asr import transcribe_bytes

        text, duration_ms = transcribe_bytes(data, suffix=suffix)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"转写失败: {exc}") from exc
    return VoiceTranscribeResponse(text=text, duration_ms=duration_ms)


@router.post("/voice/command", response_model=VoiceCommandResponse)
async def voice_command(
    _: str = Depends(get_current_user),
    audio: UploadFile = File(...),
):
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="音频为空")
    suffix = ".webm"
    if audio.filename and "." in audio.filename:
        suffix = "." + audio.filename.rsplit(".", 1)[-1].lower()
    try:
        from sensehub.perception.asr import transcribe_bytes

        text, _ = transcribe_bytes(data, suffix=suffix)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"转写失败: {exc}") from exc
    if not text:
        return VoiceCommandResponse(text="", matched=False, message="未识别到语音")
    result = await run_voice_command(text)
    return VoiceCommandResponse(**result)


@router.post("/voice/run", response_model=VoiceCommandResponse)
async def voice_run_text(
    body: TaskCreate,
    _: str = Depends(get_current_user),
):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="文本为空")
    result = await run_voice_command(
        text, history=[h.model_dump() for h in body.history], session_id=body.session_id
    )
    return VoiceCommandResponse(**result)
