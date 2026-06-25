"""工具注册表与操作级别."""

from __future__ import annotations

import time
from typing import Any, Callable

from sensehub.cognition.vision_agent import gui_agent_sync
from sensehub.execution.kill_switch import is_killed
from sensehub.execution.browser.playwright_browser import (
    browser_act,
    browser_navigate,
    browser_snapshot,
    browser_status,
    browser_tabs,
)
from sensehub.execution.tools import agent_ops, browser, clipboard, desktop, document_gen, document_script, file_ops, gui, images, perception, research, screenshot, system, virtual
from sensehub.models.schemas import PlanStep, StepResult

ToolFn = Callable[[dict[str, Any]], dict[str, Any]]


def _gui_agent_tool(params: dict[str, Any]) -> dict[str, Any]:
    result = gui_agent_sync(params)
    if not result.get("success"):
        raise RuntimeError(result.get("error") or result.get("message") or "VLM GUI Agent 未成功")
    return result


REGISTRY: dict[str, tuple[ToolFn, str]] = {
    # 桌面 / 窗口
    "open_app": (desktop.open_app, "L1"),
    "close_app": (desktop.close_app, "L1"),
    "focus_window": (desktop.focus_window, "L1"),
    "minimize_window": (desktop.minimize_window, "L1"),
    "maximize_window": (desktop.maximize_window, "L1"),
    "list_windows": (desktop.list_windows, "L0"),
    "active_window": (desktop.active_window, "L0"),
    "type_text": (desktop.type_text, "L1"),
    "save_notepad": (desktop.save_notepad, "L1"),
    "notepad_type_save": (desktop.notepad_type_save, "L1"),
    "wechat_send_message": (desktop.wechat_send_message, "L1"),
    "press_key": (desktop.press_key, "L1"),
    # 键鼠
    "click": (gui.click, "L1"),
    "double_click": (gui.double_click, "L1"),
    "scroll": (gui.scroll, "L1"),
    "hotkey": (gui.hotkey, "L1"),
    "wait": (gui.wait, "L0"),
    # 浏览器
    "web_search": (browser.web_search, "L1"),
    "open_url": (browser.open_url, "L1"),
    "browser_status": (browser_status, "L0"),
    "browser_navigate": (browser_navigate, "L1"),
    "browser_snapshot": (browser_snapshot, "L0"),
    "browser_act": (browser_act, "L1"),
    "browser_tabs": (browser_tabs, "L0"),
    # 信息检索（returns_data，供应答脑引用）
    "fetch_url": (research.fetch_url, "L0"),
    "web_search_results": (research.web_search_results, "L0"),
    "search_images": (images.search_images, "L0"),
    "download_image": (images.download_image, "L1"),
    "search_and_download_image": (images.search_and_download_image, "L1"),
    "get_weather": (research.get_weather, "L0"),
    # 文件
    "list_dir": (file_ops.list_dir, "L0"),
    "read_file": (file_ops.read_file, "L0"),
    "write_file": (file_ops.write_file, "L2"),
    "generate_document": (document_gen.generate_document, "L2"),
    "run_document_script": (document_script.run_document_script, "L2"),
    "copy_file": (file_ops.copy_file, "L2"),
    "file_exists": (file_ops.file_exists, "L0"),
    "open_folder": (file_ops.open_folder, "L1"),
    # 剪贴板
    "get_clipboard": (clipboard.get_clipboard, "L0"),
    "set_clipboard": (clipboard.set_clipboard, "L1"),
    # 系统
    "get_datetime": (system.get_datetime, "L0"),
    "notify": (system.notify, "L1"),
    "run_command": (system.run_command, "L2"),
    # Agent 任务
    "get_task_status": (agent_ops.get_task_status, "L0"),
    "cancel_tasks": (agent_ops.cancel_tasks, "L1"),
    # 虚拟屏
    "virtual_screen_start": (virtual.virtual_screen_start, "L1"),
    "virtual_screen_stop": (virtual.virtual_screen_stop, "L1"),
    "virtual_keyboard_toggle": (virtual.virtual_keyboard_toggle, "L1"),
    # 感知
    "screenshot": (screenshot.run, "L1"),
    "get_perception_state": (perception.get_perception_state, "L0"),
    # VLM 兜底
    "gui_agent": (_gui_agent_tool, "L1"),
}


def execute_step(step: PlanStep) -> StepResult:
    if is_killed():
        return StepResult(step_id=step.step_id, success=False, error="Kill Switch 已激活")

    entry = REGISTRY.get(step.tool)
    if not entry:
        return StepResult(
            step_id=step.step_id,
            success=False,
            error=f"未知工具: {step.tool}",
        )

    _, default_level = entry
    fn = entry[0]
    start = time.perf_counter()
    try:
        output = fn(step.params)
        duration = int((time.perf_counter() - start) * 1000)
        return StepResult(
            step_id=step.step_id,
            success=True,
            output=output,
            screenshot_path=output.get("screenshot_path"),
            duration_ms=duration,
        )
    except Exception as exc:
        duration = int((time.perf_counter() - start) * 1000)
        return StepResult(
            step_id=step.step_id,
            success=False,
            error=str(exc),
            duration_ms=duration,
        )
