"""请求级上下文（LLM 用量归属用户）."""

from __future__ import annotations

from contextvars import ContextVar

_llm_usage_user_id: ContextVar[str] = ContextVar("llm_usage_user_id", default="")


def set_llm_usage_user(user_id: str) -> None:
    _llm_usage_user_id.set(str(user_id or "").strip())


def get_llm_usage_user() -> str:
    return _llm_usage_user_id.get() or ""
