"""灵枢 Chat 模型调用错误与用户提示."""

from __future__ import annotations

import httpx

from sensehub.config.user_settings import get_provider_credentials
from sensehub.cognition.studio_models import StudioModelRoute

CHAT_MODEL_UNAVAILABLE_MSG = "当前模型不可用，请切换其他模型"


class ChatModelUnavailableError(RuntimeError):
    """所选 Chat 模型无法调用（缺 Key、API 报错、空响应等）."""

    def __init__(self, message: str = CHAT_MODEL_UNAVAILABLE_MSG) -> None:
        super().__init__(message)


def assert_chat_route_ready(route: StudioModelRoute | None) -> None:
    """发消息前检查：所选模型提供商是否已配置 Key."""
    if route is None or not route.available:
        return
    _, key = get_provider_credentials(route.provider)
    if not key:
        raise ChatModelUnavailableError()


def normalize_chat_model_error(exc: Exception) -> str:
    """将底层 API 异常统一为用户可读提示."""
    if isinstance(exc, ChatModelUnavailableError):
        return str(exc) or CHAT_MODEL_UNAVAILABLE_MSG

    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403, 404, 402, 429, 500, 502, 503):
            return CHAT_MODEL_UNAVAILABLE_MSG

    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)):
        return CHAT_MODEL_UNAVAILABLE_MSG

    text = str(exc).lower()
    if any(
        k in text
        for k in (
            "api key",
            "api_key",
            "authentication",
            "unauthorized",
            "invalid_api_key",
            "model api",
            "not found",
            "does not exist",
            "insufficient",
            "余额",
            "quota",
        )
    ):
        return CHAT_MODEL_UNAVAILABLE_MSG

    return str(exc).strip() or CHAT_MODEL_UNAVAILABLE_MSG
