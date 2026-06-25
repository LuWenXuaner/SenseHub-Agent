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
from sensehub.execution.browser.playwright_enhanced import (
    browser_click as pw_browser_click,
    browser_fill as pw_browser_fill,
    browser_get_text as pw_browser_get_text,
    browser_get_html as pw_browser_get_html,
    browser_wait as pw_browser_wait,
    browser_scroll as pw_browser_scroll,
    browser_new_tab,
    browser_switch_tab,
    browser_close_tab,
    browser_list_tabs,
    browser_go_back,
    browser_go_forward,
    browser_reload,
    browser_evaluate,
    browser_screenshot as pw_browser_screenshot,
)
from sensehub.execution.tools import agent_ops, browser, clipboard, desktop, file_ops, gui, research, screenshot, system, virtual
from sensehub.execution.tools import gui_enhanced, file_ops_enhanced, screenshot_enhanced
from sensehub.execution.tools.screenshot_interactive import capture_interactive_region
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
    "press_key": (desktop.press_key, "L1"),
    # 键鼠
    "click": (gui.click, "L1"),
    "double_click": (gui.double_click, "L1"),
    "right_click": (gui_enhanced.right_click, "L1"),
    "scroll": (gui.scroll, "L1"),
    "hotkey": (gui.hotkey, "L1"),
    "wait": (gui.wait, "L0"),
    "move_to": (gui_enhanced.move_to, "L0"),
    "get_position": (gui_enhanced.get_position, "L0"),
    "drag": (gui_enhanced.drag, "L1"),
    "click_image": (gui_enhanced.click_image, "L1"),
    "locate_image": (gui_enhanced.locate_image, "L0"),
    # 浏览器
    "web_search": (browser.web_search, "L1"),
    "open_url": (browser.open_url, "L1"),
    "browser_status": (browser_status, "L0"),
    "browser_navigate": (browser_navigate, "L1"),
    "browser_snapshot": (browser_snapshot, "L0"),
    "browser_act": (browser_act, "L1"),
    "browser_tabs": (browser_tabs, "L0"),
    "browser_click": (pw_browser_click, "L1"),
    "browser_fill": (pw_browser_fill, "L1"),
    "browser_get_text": (pw_browser_get_text, "L0"),
    "browser_get_html": (pw_browser_get_html, "L0"),
    "browser_wait": (pw_browser_wait, "L0"),
    "browser_scroll": (pw_browser_scroll, "L1"),
    "browser_new_tab": (browser_new_tab, "L1"),
    "browser_switch_tab": (browser_switch_tab, "L1"),
    "browser_close_tab": (browser_close_tab, "L1"),
    "browser_list_tabs": (browser_list_tabs, "L0"),
    "browser_go_back": (browser_go_back, "L1"),
    "browser_go_forward": (browser_go_forward, "L1"),
    "browser_reload": (browser_reload, "L1"),
    "browser_evaluate": (browser_evaluate, "L0"),
    "browser_screenshot": (pw_browser_screenshot, "L0"),
    # 信息检索（returns_data，供应答脑引用）
    "fetch_url": (research.fetch_url, "L0"),
    "get_weather": (research.get_weather, "L0"),
    # 文件
    "list_dir": (file_ops.list_dir, "L0"),
    "read_file": (file_ops.read_file, "L0"),
    "write_file": (file_ops.write_file, "L2"),
    "copy_file": (file_ops.copy_file, "L2"),
    "file_exists": (file_ops.file_exists, "L0"),
    "open_folder": (file_ops.open_folder, "L1"),
    "move_file": (file_ops_enhanced.move_file, "L2"),
    "rename_file": (file_ops_enhanced.rename_file, "L2"),
    "delete_file": (file_ops_enhanced.delete_file, "L2"),
    "search_files": (file_ops_enhanced.search_files, "L0"),
    "get_file_info": (file_ops_enhanced.get_file_info, "L0"),
    "ensure_directory": (file_ops_enhanced.ensure_directory, "L1"),
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
    "capture_region": (screenshot_enhanced.capture_region, "L0"),
    "capture_window": (screenshot_enhanced.capture_window, "L0"),
    "capture_region_interactive": (capture_interactive_region, "L0"),
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
