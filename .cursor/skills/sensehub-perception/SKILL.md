---
name: sensehub-perception
description: SenseHub camera, vision, ASR modules. Use when editing sensehub/perception/ or Phase 2+ multimodal features.
---

# SenseHub Perception

## Phase 2 scope

- Camera: OpenCV, `CAMERA_INDEX` from local.env
- Vision: YOLO weights from `paths.yaml` → `models.yolo_weights`
- ASR: faster-whisper at `models.whisper_model`; mic `MIC_DEVICE_NAME`

## Event format

```python
{"type": "person_detected|speech_text|gesture", "confidence": float, "payload": {}, "timestamp": iso, "source": "camera|mic"}
```

## Rules

- Camera/mic default OFF; user enables in UI
- Model paths from yaml only
- Web preview via WebSocket `/ws/camera` (Phase 2)
- Do not upload frames to cloud unless vision LLM explicitly invoked

## Virtual screen (Phase 4, Max)

MediaPipe Hands + calibration; TierGate in UI
