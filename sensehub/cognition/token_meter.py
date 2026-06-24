"""离线 Token 计数（DeepSeek V3 tokenizer，项目内 deepseek_v3_tokenizer/）."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

_TOKENIZER_DIR = Path(__file__).resolve().parents[2] / "deepseek_v3_tokenizer"


@lru_cache(maxsize=1)
def _load_tokenizer():
    try:
        import transformers  # type: ignore
    except ImportError as exc:
        raise RuntimeError("请安装 transformers：pip install transformers") from exc
    if not (_TOKENIZER_DIR / "tokenizer.json").is_file():
        raise FileNotFoundError(f"未找到 tokenizer：{_TOKENIZER_DIR}")
    return transformers.AutoTokenizer.from_pretrained(str(_TOKENIZER_DIR), trust_remote_code=True)


def count_text_tokens(text: str) -> int:
    """单段文本 token 数；失败时按字符粗估."""
    raw = str(text or "")
    if not raw:
        return 0
    try:
        tok = _load_tokenizer()
        return len(tok.encode(raw, add_special_tokens=False))
    except Exception:
        return max(1, len(raw) // 2)


def _content_to_str(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text") or ""))
                elif block.get("type") == "image_url":
                    parts.append("[image]")
        return "\n".join(p for p in parts if p)
    if content is None:
        return ""
    return str(content)


def count_messages_tokens(messages: list[dict[str, Any]]) -> int:
    """估算 messages 列表 prompt token（role + content 拼接后计数）."""
    lines: list[str] = []
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or "")
        body = _content_to_str(msg.get("content"))
        if role or body:
            lines.append(f"{role}\n{body}".strip())
    return count_text_tokens("\n\n".join(lines))


def estimate_chat_tokens(
    messages: list[dict[str, Any]],
    completion: str,
    *,
    api_usage: dict[str, Any] | None = None,
) -> tuple[int, int]:
    """返回 (prompt_tokens, completion_tokens)；优先 API usage，否则离线估算."""
    usage = api_usage if isinstance(api_usage, dict) else {}
    prompt = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    if prompt > 0 and completion_tokens > 0:
        return prompt, completion_tokens
    if prompt > 0:
        return prompt, completion_tokens or count_text_tokens(completion)
    if completion_tokens > 0:
        return count_messages_tokens(messages), completion_tokens
    return count_messages_tokens(messages), count_text_tokens(completion)
