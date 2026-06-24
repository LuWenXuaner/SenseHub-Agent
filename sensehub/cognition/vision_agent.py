"""VLM 驱动的 GUI Agent：截图 → 决策 → 键鼠 → 验证."""

from __future__ import annotations

import asyncio
from typing import Any

from sensehub.cognition.router import LLMRouter
from sensehub.execution.kill_switch import is_killed
from sensehub.execution.tools import desktop, gui
from sensehub.execution.tools import screenshot as screenshot_tool
from sensehub.settings import get_settings

MAX_STEPS = 10

VISION_ACT_SYSTEM = """你是 Windows 桌面 GUI 操作助手。根据截图和用户目标，输出**唯一 JSON**（不要 markdown）：

{
  "thought": "简短分析当前界面",
  "action": "click|right_click|double_click|type|hotkey|scroll|wait|done|fail",
  "x": 0,
  "y": 0,
  "text": "要输入的文字（action=type 时）",
  "keys": ["win"],
  "scroll": -3,
  "seconds": 1,
  "done": false,
  "message": "给用户的状态说明"
}

规则：
- x/y 使用 0–1000 归一化坐标（相对屏幕宽高）
- 一次只做一个动作
- 关闭窗口：点击关闭按钮、Alt+F4 或右键菜单
- 下载/保存图片：在浏览器中右键或点击下载按钮，按界面实际元素操作
- 目标已完成时 action=done 且 done=true
- 无法继续时 action=fail
- 打开记事本：可 Win 键搜索、任务栏点击或已知入口
- 不要输出 L3 危险操作
"""

VERIFY_SYSTEM = """你是任务验收助手。根据截图判断用户目标是否已完成。
只输出 JSON：{"passed": true|false, "reason": "..."}"""


def _check_vlm_ready() -> None:
    settings = get_settings()
    if not settings.siliconflow_api_key and not settings.volcengine_api_key:
        raise RuntimeError("未配置 VLM API Key（local.env 中 SILICONFLOW_API_KEY 等）")


def _execute_action(step: dict[str, Any]) -> dict[str, Any]:
    action = (step.get("action") or "").lower()
    if action == "click":
        return gui.click(step)
    if action == "right_click":
        return gui.click({**step, "button": "right"})
    if action == "double_click":
        return gui.double_click(step)
    if action == "scroll":
        return gui.scroll(step)
    if action == "hotkey":
        return gui.hotkey(step)
    if action == "wait":
        return gui.wait(step)
    if action == "type":
        return desktop.type_text({"text": step.get("text", "")})
    if action in ("done", "fail"):
        return {"action": action, "message": step.get("message", "")}
    raise ValueError(f"未知 VLM 动作: {action}")


async def _verify(router: LLMRouter, intent: str, image_b64: str) -> tuple[bool, str]:
    data = await router.chat_vision_json(
        "vision",
        VERIFY_SYSTEM,
        f"用户目标：{intent}\n请判断目标是否已在当前界面完成。",
        image_b64,
    )
    return bool(data.get("passed")), str(data.get("reason", ""))


async def run_gui_agent(intent: str, *, max_steps: int = MAX_STEPS) -> dict[str, Any]:
    _check_vlm_ready()
    router = LLMRouter()
    history: list[dict[str, Any]] = []
    last_shot: str | None = None

    for step_idx in range(max_steps):
        if is_killed():
            return {
                "success": False,
                "intent": intent,
                "steps": history,
                "screenshot_path": last_shot,
                "error": "用户已停止执行",
                "method": "vlm-gui-agent",
            }

        shot = screenshot_tool.run({"mode": "fullscreen"})
        last_shot = shot["screenshot_path"]
        image_b64 = gui.encode_image_file(last_shot)

        prev = history[-1] if history else None
        user_prompt = (
            f"用户目标：{intent}\n"
            f"当前步骤：{step_idx + 1}/{max_steps}\n"
            f"上一步结果：{prev}\n"
            "请决定下一步操作。"
        )

        decision = await router.chat_vision_json(
            "vision", VISION_ACT_SYSTEM, user_prompt, image_b64
        )
        action = (decision.get("action") or "").lower()

        if action == "fail":
            return {
                "success": False,
                "intent": intent,
                "steps": history,
                "screenshot_path": last_shot,
                "error": decision.get("message") or decision.get("thought") or "VLM 判定失败",
                "method": "vlm-gui-agent",
            }

        if action == "done" or decision.get("done"):
            passed, reason = await _verify(router, intent, image_b64)
            history.append({"step": step_idx + 1, "action": "done", "verify": reason, **decision})
            return {
                "success": passed,
                "intent": intent,
                "steps": history,
                "screenshot_path": last_shot,
                "message": reason or decision.get("message", "任务完成"),
                "method": "vlm-gui-agent",
            }

        try:
            output = _execute_action(decision)
            history.append(
                {
                    "step": step_idx + 1,
                    "action": action,
                    "thought": decision.get("thought"),
                    "output": output,
                }
            )
        except Exception as exc:
            history.append({"step": step_idx + 1, "action": action, "error": str(exc)})
            return {
                "success": False,
                "intent": intent,
                "steps": history,
                "screenshot_path": last_shot,
                "error": str(exc),
                "method": "vlm-gui-agent",
            }

        await asyncio.sleep(0.5)

    return {
        "success": False,
        "intent": intent,
        "steps": history,
        "screenshot_path": last_shot,
        "error": f"超过最大步数 {max_steps}",
        "method": "vlm-gui-agent",
    }


def gui_agent_sync(params: dict[str, Any]) -> dict[str, Any]:
    intent = (params.get("intent") or params.get("query") or "").strip()
    if not intent:
        raise ValueError("intent 不能为空")
    max_steps = int(params.get("max_steps", MAX_STEPS))
    return asyncio.run(run_gui_agent(intent, max_steps=max_steps))
