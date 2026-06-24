"""工具目录：供规划脑 / 意图脑引用（程序化优先，VLM 兜底）."""

from __future__ import annotations

TOOL_CATALOG: dict[str, dict] = {
    # --- 桌面 / 窗口 ---
    "open_app": {
        "category": "desktop",
        "risk": "L1",
        "returns_data": False,
        "side_effect": "若已在运行则聚焦主窗口，否则启动",
        "desc": "打开应用；已在运行时不会重复启动（reuse_if_open 默认 true）",
        "params": {"name": "str", "focus": "bool=true", "reuse_if_open": "bool=true"},
    },
    "close_app": {
        "category": "desktop",
        "risk": "L1",
        "desc": "按窗口标题关闭应用（Alt+F4）",
        "params": {"title": "str"},
    },
    "focus_window": {
        "category": "desktop",
        "risk": "L1",
        "desc": "窗口置前",
        "params": {"title": "str"},
    },
    "minimize_window": {
        "category": "desktop",
        "risk": "L1",
        "desc": "最小化匹配窗口",
        "params": {"title": "str"},
    },
    "maximize_window": {
        "category": "desktop",
        "risk": "L1",
        "desc": "最大化匹配窗口",
        "params": {"title": "str"},
    },
    "list_windows": {
        "category": "desktop",
        "risk": "L0",
        "returns_data": True,
        "desc": "列出可见窗口标题",
        "params": {"limit": "int=40"},
    },
    "active_window": {
        "category": "desktop",
        "risk": "L0",
        "returns_data": True,
        "desc": "当前前台窗口标题（操作前确认焦点）",
        "params": {},
    },
    "type_text": {
        "category": "desktop",
        "risk": "L1",
        "desc": "向焦点窗口输入文本（支持中文粘贴）",
        "params": {"text": "str", "app": "str?"},
    },
    "press_key": {
        "category": "desktop",
        "risk": "L1",
        "desc": "单键或组合键",
        "params": {"keys": "list[str] 或 key=str"},
    },
    # --- 键鼠坐标 ---
    "click": {"category": "gui", "risk": "L1", "desc": "点击坐标", "params": {"x": "float", "y": "float", "button": "left|right"}},
    "double_click": {"category": "gui", "risk": "L1", "desc": "双击", "params": {"x": "float", "y": "float"}},
    "scroll": {"category": "gui", "risk": "L1", "desc": "滚轮", "params": {"clicks": "int", "x": "float?", "y": "float?"}},
    "hotkey": {"category": "gui", "risk": "L1", "desc": "快捷键", "params": {"keys": "list[str]"}},
    "wait": {"category": "gui", "risk": "L0", "desc": "等待秒数", "params": {"seconds": "float"}},
    # --- 浏览器 ---
    "web_search": {
        "category": "browser",
        "risk": "L1",
        "returns_data": False,
        "side_effect": "在 Edge 打开搜索页（不返回搜索结果正文）",
        "desc": "Edge 默认搜索引擎打开搜索页",
        "params": {"query": "str"},
    },
    "open_url": {
        "category": "browser",
        "risk": "L1",
        "returns_data": False,
        "side_effect": "在 Edge 打开 URL（不返回网页正文）",
        "desc": "Edge 打开 URL",
        "params": {"url": "str"},
    },
    "browser_status": {
        "category": "browser",
        "risk": "L0",
        "returns_data": True,
        "desc": "Playwright 浏览器状态",
        "params": {},
    },
    "browser_navigate": {
        "category": "browser",
        "risk": "L1",
        "returns_data": True,
        "desc": "Playwright 打开 URL",
        "params": {"url": "str"},
    },
    "browser_snapshot": {
        "category": "browser",
        "risk": "L0",
        "returns_data": True,
        "desc": "页面 DOM ref 快照（snapshot-act 循环）",
        "params": {"screenshot": "bool=true"},
    },
    "browser_act": {
        "category": "browser",
        "risk": "L1",
        "returns_data": True,
        "desc": "按 ref 操作页面：click/fill/press",
        "params": {"ref": "str", "action": "str=click", "value": "str?"},
    },
    "browser_tabs": {
        "category": "browser",
        "risk": "L0",
        "returns_data": True,
        "desc": "浏览器标签页信息",
        "params": {},
    },
    "fetch_url": {
        "category": "research",
        "risk": "L0",
        "returns_data": True,
        "desc": "HTTP 抓取网页/JSON 并提取可读文本（不打开浏览器窗口）",
        "params": {"url": "str"},
    },
    "get_weather": {
        "category": "research",
        "risk": "L0",
        "returns_data": True,
        "desc": "查询城市天气预报（返回结构化数据，供旅游/出行建议引用）",
        "params": {"location": "str", "days": "int=2", "lang": "str=zh"},
    },
    # --- 文件（限制在 DATA_ROOT / 用户目录） ---
    "list_dir": {
        "category": "file",
        "risk": "L0",
        "returns_data": True,
        "desc": "列出目录",
        "params": {"path": "str", "limit": "int=100"},
    },
    "read_file": {
        "category": "file",
        "risk": "L0",
        "returns_data": True,
        "desc": "读取文本文件",
        "params": {"path": "str", "max_bytes": "int=65536"},
    },
    "write_file": {
        "category": "file",
        "risk": "L2",
        "desc": "写入文本文件",
        "params": {"path": "str", "content": "str", "append": "bool=false"},
    },
    "copy_file": {
        "category": "file",
        "risk": "L2",
        "desc": "复制文件",
        "params": {"src": "str", "dst": "str"},
    },
    "file_exists": {
        "category": "file",
        "risk": "L0",
        "desc": "检查路径是否存在",
        "params": {"path": "str"},
    },
    "open_folder": {
        "category": "file",
        "risk": "L1",
        "desc": "资源管理器打开文件夹",
        "params": {"path": "str"},
    },
    # --- 剪贴板 ---
    "get_clipboard": {"category": "clipboard", "risk": "L0", "returns_data": True, "desc": "读取剪贴板文本", "params": {}},
    "set_clipboard": {"category": "clipboard", "risk": "L1", "desc": "写入剪贴板", "params": {"text": "str"}},
    # --- 系统 ---
    "get_datetime": {"category": "system", "risk": "L0", "returns_data": True, "desc": "当前日期时间", "params": {}},
    "notify": {
        "category": "system",
        "risk": "L1",
        "desc": "Windows  toast 通知",
        "params": {"title": "str", "message": "str"},
    },
    "run_command": {
        "category": "system",
        "risk": "L2",
        "desc": "运行受白名单限制的 shell 命令",
        "params": {"command": "str", "shell": "bool=false"},
    },
    # --- 感知 ---
    "screenshot": {
        "category": "perception",
        "risk": "L1",
        "returns_data": True,
        "desc": "截屏",
        "params": {"mode": "fullscreen|active_window"},
    },
    "get_task_status": {
        "category": "agent",
        "risk": "L0",
        "returns_data": True,
        "desc": "查询当前/最近任务状态",
        "params": {"limit": "int=5"},
    },
    "cancel_tasks": {
        "category": "agent",
        "risk": "L1",
        "desc": "取消运行中任务",
        "params": {"scope": "active|all"},
    },
    "virtual_screen_start": {
        "category": "virtual",
        "risk": "L1",
        "desc": "开启虚拟屏（Max）",
        "params": {},
    },
    "virtual_screen_stop": {
        "category": "virtual",
        "risk": "L1",
        "desc": "关闭虚拟屏",
        "params": {},
    },
    "virtual_keyboard_toggle": {
        "category": "virtual",
        "risk": "L1",
        "desc": "显示/隐藏虚拟键盘",
        "params": {"enabled": "bool"},
    },
    # --- VLM 兜底 ---
    "gui_agent": {
        "category": "vision",
        "risk": "L1",
        "desc": "看屏幕自主操作（贵，仅未知 UI / 网页内点击）",
        "params": {"intent": "str", "max_steps": "int=10"},
    },
}


def tool_returns_data(tool: str) -> bool:
    return bool(TOOL_CATALOG.get(tool, {}).get("returns_data"))


def format_tools_for_planner() -> str:
    lines = ["可用工具（tool）按类别。注意 returns_data：true=结果可写入回答，false=仅副作用操作。"]
    by_cat: dict[str, list[str]] = {}
    for name, meta in TOOL_CATALOG.items():
        cat = meta.get("category", "other")
        by_cat.setdefault(cat, []).append(name)
    cat_labels = {
        "desktop": "桌面/窗口",
        "gui": "键鼠坐标",
        "browser": "浏览器",
        "research": "信息检索",
        "file": "文件",
        "clipboard": "剪贴板",
        "system": "系统",
        "perception": "感知",
        "agent": "Agent/任务",
        "virtual": "虚拟屏",
        "vision": "视觉兜底",
    }
    for cat, tools in by_cat.items():
        lines.append(f"\n### {cat_labels.get(cat, cat)}")
        for t in tools:
            m = TOOL_CATALOG[t]
            params = ", ".join(f'{k}: {v}' for k, v in m.get("params", {}).items()) or "无"
            returns = "returns_data=true" if m.get("returns_data") else "returns_data=false"
            lines.append(f"- {t} [{m.get('risk', 'L1')}, {returns}]: {m['desc']} | params: {params}")
    return "\n".join(lines)
