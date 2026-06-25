"""分段计时：微信发消息各步骤耗时（在项目根目录执行）."""
from __future__ import annotations

import time

from sensehub.cognition.quick_match import match_atomic_plan
from sensehub.execution.tools import desktop
from sensehub.execution.tools.registry import execute_step


def _mark(name: str, t0: float, marks: list[tuple[str, int]]) -> float:
    now = time.perf_counter()
    marks.append((name, int((now - t0) * 1000)))
    return now


def main() -> None:
    text = "打开微信，给文件传输助手发送你好"
    plan = match_atomic_plan(text)
    if not plan:
        print("未命中原子捷径")
        return
    step = plan.steps[0]
    print("params:", step.params)

    marks: list[tuple[str, int]] = []
    t = time.perf_counter()

    # 手动走 wechat_send_message 内部分段（与工具实现同步）
    params = dict(step.params)
    contact = str(params.get("contact") or "")
    message = str(params.get("message") or "")
    app = "微信"
    keywords, process_images = desktop._resolve_app_target(app)
    t = _mark("resolve_app", t, marks)
    existing = desktop._existing_app_windows(keywords, process_images)
    t = _mark("find_windows", t, marks)
    if not existing:
        print("未检测到微信窗口，跳过桌面段")
    else:
        best = desktop._pick_best_window(existing)
        if best:
            hwnd, _ = best
            desktop._focus_hwnd(hwnd, click_center=False, app_for_click=app, post_focus_wait=0.06, aggressive=False)
        t = _mark("focus", t, marks)
        desktop._hotkey_names("ctrl", "f")
        time.sleep(0.15)
        t = _mark("ctrl_f", t, marks)
        desktop._hotkey_names("ctrl", "a")
        time.sleep(0.03)
        desktop._paste_text(contact)
        time.sleep(0.5)
        t = _mark("search_contact", t, marks)
        desktop._press_vk(desktop._VK["enter"])
        time.sleep(0.3)
        t = _mark("open_chat", t, marks)
        desktop._paste_text(message)
        time.sleep(0.04)
        t = _mark("paste_message", t, marks)
        desktop._press_vk(desktop._VK["enter"])
        t = _mark("send", t, marks)

    print("\n--- 分段耗时 (ms) ---")
    for name, ms in marks:
        print(f"  {name}: {ms}")
    print("\n--- 整步 execute_step ---")
    t0 = time.perf_counter()
    result = execute_step(step)
    total = int((time.perf_counter() - t0) * 1000)
    print(f"  success={result.success} error={result.error} duration_ms={result.duration_ms} wall={total}")


if __name__ == "__main__":
    main()
