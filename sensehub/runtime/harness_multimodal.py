"""Max 档多模态执行提示."""

from __future__ import annotations

from sensehub.licensing.tier import feature_enabled


def multimodal_prompt_addon() -> str:
    parts: list[str] = []
    if feature_enabled("virtual_screen"):
        parts.append(
            "虚拟屏已启用：可用 virtual_screen_start、手势映射点击；复杂桌面 UI 优先程序化工具，必要时 gui_agent。"
        )
    if feature_enabled("voice_stream"):
        parts.append("语音通道与 Hub 共用同一 Agent Runtime。")
    if feature_enabled("multi_agent"):
        parts.append("自主模式子目标均走 AgentRuntime，勿假定前置步骤已成功。")
    if not parts:
        return ""
    return "【多模态 Max/Pro】\n" + "\n".join(parts)
