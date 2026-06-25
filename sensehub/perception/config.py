"""感知配置（config/perception.yaml）."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from sensehub.settings import CONFIG_DIR, get_settings

_DEFAULT: dict[str, Any] = {
    "preview_interval_ms": 100,
    "detect_every_n_frames": 5,
    "gesture_every_n_frames": 5,
    "gesture_only_if_person": True,
    "gesture_backend": "mediapipe",
    "jpeg_quality": 55,
    "camera_mirror": True,
    "virtual_pointer_every_n_frames": 1,
    "pointer_smooth_alpha": 0.78,
    "pointer_track_alpha": 0.72,
    "pointer_deadzone_px": 0,
    "virtual_track_hold_frames": 3,
    "virtual_pinch_threshold": 0.058,
    "virtual_pinch_confirm_frames": 2,
    "virtual_click_cooldown_sec": 0.35,
    "gesture_min_confidence": 0.62,
    "gesture_confirm_frames": 3,
    "gesture_hold_sec": 1.2,
    "wave_min_span": 0.18,
    "wave_min_reversals": 4,
    "nod_min_y_range": 0.034,
    "nod_max_y_range": 0.11,
    "nod_min_reversals": 4,
    "shake_min_x_range": 0.048,
    "shake_max_x_range": 0.12,
    "shake_min_reversals": 4,
    "hand_raise_min_delta": 0.09,
    # 虚拟屏映射：direct=画面比例直接映射；homography=九点精细校准
    "virtual_screen_mapping": "direct",
}


@lru_cache
def get_perception_config() -> dict[str, Any]:
    import yaml

    path = CONFIG_DIR / "perception.yaml"
    merged = dict(_DEFAULT)
    if path.is_file():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(raw.get("perception"), dict):
            merged.update(raw["perception"])
    settings = get_settings()
    models = settings.paths.get("models", {})
    if models.get("hand_landmarker"):
        merged["hand_landmarker"] = str(models["hand_landmarker"])
    if models.get("face_landmarker"):
        merged["face_landmarker"] = str(models["face_landmarker"])
    root = settings.models_root or str(get_settings().sensehub_root)
    merged.setdefault(
        "hand_landmarker",
        str(__import__("pathlib").Path(root) / "hand_landmarker.task"),
    )
    merged.setdefault(
        "face_landmarker",
        str(__import__("pathlib").Path(root) / "face_landmarker.task"),
    )
    return merged


def reload_perception_config() -> dict[str, Any]:
    get_perception_config.cache_clear()
    return get_perception_config()
