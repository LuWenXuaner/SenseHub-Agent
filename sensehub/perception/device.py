"""推理设备选择（CUDA / CPU）."""

from __future__ import annotations

from functools import lru_cache

from sensehub.settings import get_settings


@lru_cache
def _torch_cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def inference_device() -> str:
    settings = get_settings()
    if settings.use_cuda and _torch_cuda_available():
        return "cuda:0"
    return "cpu"


def inference_device_label() -> str:
    device = inference_device()
    if not device.startswith("cuda"):
        return "cpu"
    try:
        import torch

        return torch.cuda.get_device_name(0)
    except Exception:
        return device
