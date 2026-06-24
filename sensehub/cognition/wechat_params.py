"""微信发消息参数：由 LLM 从用户原话提取 contact / message（不用正则硬截）."""

from __future__ import annotations

import re
from typing import Any

from sensehub.cognition.router import LLMRouter

_WECHAT_EXTRACT_SYSTEM = """你是参数提取器。从用户关于「微信发消息」的自然语言指令中提取 JSON（不要 markdown）：
{
  "contact": "完整联系人或会话名称",
  "message": "要输入的完整消息正文",
  "send": true
}

规则：
- contact、message 必须与用户意图一致，完整书写，禁止截断（例：「文件传输助手」不能写成「文件传」，「你好」不能写成「你」）
- send 仅当用户明确说「不发送/不要发送/别发送」时为 false，否则 true
- 只输出 JSON 对象"""


async def extract_wechat_send_params(user_text: str) -> dict[str, Any]:
    text = user_text.strip()
    if not text:
        raise ValueError("无法从空指令提取微信参数")
    router = LLMRouter()
    raw = await router.chat_json("intent", _WECHAT_EXTRACT_SYSTEM, text)
    if not isinstance(raw, dict):
        raise ValueError("微信参数提取失败")
    contact = str(raw.get("contact") or raw.get("name") or "").strip()
    message = str(raw.get("message") or raw.get("text") or "").strip()
    if not contact or not message:
        raise ValueError("未能从指令中识别微信联系人或消息内容")
    send = bool(raw.get("send", True))
    if re.search(r"不发送|不要发送|别发送", text):
        send = False
    return {"contact": contact, "message": message, "send": send}


async def resolve_wechat_message_params(user_text: str, partial: dict[str, Any] | None) -> dict[str, Any]:
    """执行 wechat_send_message 前始终以用户原话为准做 LLM 提取."""
    merged = await extract_wechat_send_params(user_text)
    if partial and "send" in partial:
        merged["send"] = bool(partial.get("send"))
    return merged
