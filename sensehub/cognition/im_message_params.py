"""IM 发消息参数：由 LLM 从用户原话提取 contact / message（不用正则硬截）."""

from __future__ import annotations

import re
from typing import Any

from sensehub.cognition.router import LLMRouter

_IM_EXTRACT_SYSTEM = """你是参数提取器。从用户关于「{app_label}发消息」的自然语言指令中提取 JSON（不要 markdown）：
{{
  "contact": "完整联系人或会话名称",
  "message": "要输入的完整消息正文",
  "send": true
}}

规则：
- contact、message 必须与用户意图一致，完整书写，禁止截断
- contact 必须是好友/联系人/群名称，绝不能把要发送的消息正文（如「你好」）填进 contact
- message 是要发送的正文；例：「给我的手机发你好」→ contact「我的手机」、message「你好」
- 例：「文件传输助手」不能写成「文件传」；「我的手机」不能写成「手机」
- 「联系人"XXX"」「会话 XXX」→ contact 为 XXX 全称，保留「我的」等修饰词
- send 仅当用户明确说「不发送/不要发送/别发送/先不要发送」时为 false，否则 true
- 只输出 JSON 对象"""


async def extract_im_send_params(user_text: str, *, app_label: str) -> dict[str, Any]:
    text = user_text.strip()
    if not text:
        raise ValueError(f"无法从空指令提取{app_label}参数")
    router = LLMRouter()
    system = _IM_EXTRACT_SYSTEM.format(app_label=app_label)
    raw = await router.chat_json("intent", system, text)
    if not isinstance(raw, dict):
        raise ValueError(f"{app_label}参数提取失败")
    contact = str(raw.get("contact") or raw.get("name") or "").strip()
    message = str(raw.get("message") or raw.get("text") or "").strip()
    if not contact or not message:
        raise ValueError(f"未能从指令中识别{app_label}联系人或消息内容")
    if contact == message:
        raise ValueError(f"联系人名与消息内容相同（{contact!r}），请检查指令表述")
    send = bool(raw.get("send", True))
    if re.search(r"不发送|不要发送|别发送|先不要发送", text):
        send = False
    return {"contact": contact, "message": message, "send": send}


async def resolve_im_message_params(
    user_text: str,
    partial: dict[str, Any] | None,
    *,
    app_label: str,
) -> dict[str, Any]:
    """执行 IM 发消息前从用户原话提取 contact/message（不信任计划里可能截断的 partial）."""
    partial = partial or {}
    merged = await extract_im_send_params(user_text, app_label=app_label)
    if "send" in partial:
        merged["send"] = bool(partial.get("send"))
    if re.search(r"不发送|不要发送|别发送|先不要发送", user_text):
        merged["send"] = False
    return merged


async def resolve_wechat_message_params(user_text: str, partial: dict[str, Any] | None) -> dict[str, Any]:
    return await resolve_im_message_params(user_text, partial, app_label="微信")
