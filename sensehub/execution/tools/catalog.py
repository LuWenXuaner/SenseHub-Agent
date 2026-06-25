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
    "right_click": {"category": "gui", "risk": "L1", "desc": "右键点击", "params": {"x": "float", "y": "float"}},
    "scroll": {"category": "gui", "risk": "L1", "desc": "滚轮", "params": {"clicks": "int", "x": "float?", "y": "float?"}},
    "hotkey": {"category": "gui", "risk": "L1", "desc": "快捷键", "params": {"keys": "list[str]"}},
    "wait": {"category": "gui", "risk": "L0", "desc": "等待秒数", "params": {"seconds": "float"}},
    "move_to": {"category": "gui", "risk": "L0", "desc": "移动鼠标到坐标", "params": {"x": "float", "y": "float", "duration": "float=0.2"}},
    "get_position": {"category": "gui", "risk": "L0", "returns_data": True, "desc": "获取鼠标当前位置", "params": {}},
    "drag": {"category": "gui", "risk": "L1", "desc": "拖拽从 start 到 end", "params": {"start_x": "float", "start_y": "float", "end_x": "float", "end_y": "float", "duration": "float=0.3"}},
    "click_image": {"category": "gui", "risk": "L1", "desc": "基于图片模板匹配点击（OpenCV 抗界面变化）", "params": {"template": "str", "confidence": "float=0.8", "button": "str=left", "retry": "int=3"}},
    "locate_image": {"category": "gui", "risk": "L0", "returns_data": True, "desc": "在屏幕上查找图片模板位置", "params": {"template": "str", "confidence": "float=0.8", "region": "list[int]?"}},
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
    # --- 增强浏览器操作 ---
    "browser_click": {
        "category": "browser",
        "risk": "L1",
        "returns_data": True,
        "desc": "按 CSS 选择器点击元素",
        "params": {"selector": "str", "timeout": "int=30000"},
    },
    "browser_fill": {
        "category": "browser",
        "risk": "L1",
        "returns_data": True,
        "desc": "按 CSS 选择器填写表单",
        "params": {"selector": "str", "value": "str", "timeout": "int=30000"},
    },
    "browser_get_text": {
        "category": "browser",
        "risk": "L0",
        "returns_data": True,
        "desc": "提取元素文本",
        "params": {"selector": "str", "timeout": "int=10000"},
    },
    "browser_get_html": {
        "category": "browser",
        "risk": "L0",
        "returns_data": True,
        "desc": "提取元素 HTML",
        "params": {"selector": "str=body", "timeout": "int=10000"},
    },
    "browser_wait": {
        "category": "browser",
        "risk": "L0",
        "returns_data": True,
        "desc": "等待元素出现/可见",
        "params": {"selector": "str", "timeout": "int=30000", "state": "str=visible"},
    },
    "browser_scroll": {
        "category": "browser",
        "risk": "L1",
        "returns_data": True,
        "desc": "滚动页面（down/up/bottom/top）",
        "params": {"direction": "str=down", "amount": "int=500"},
    },
    "browser_new_tab": {
        "category": "browser",
        "risk": "L1",
        "returns_data": True,
        "desc": "新建浏览器标签页",
        "params": {"url": "str=about:blank"},
    },
    "browser_switch_tab": {
        "category": "browser",
        "risk": "L1",
        "returns_data": True,
        "desc": "按 index/title/url 切换标签页",
        "params": {"index": "int?", "title": "str?", "url": "str?"},
    },
    "browser_close_tab": {
        "category": "browser",
        "risk": "L1",
        "returns_data": True,
        "desc": "关闭标签页（默认当前）",
        "params": {"index": "int=-1"},
    },
    "browser_list_tabs": {
        "category": "browser",
        "risk": "L0",
        "returns_data": True,
        "desc": "列出所有标签页",
        "params": {},
    },
    "browser_go_back": {
        "category": "browser",
        "risk": "L1",
        "returns_data": True,
        "desc": "浏览器后退",
        "params": {},
    },
    "browser_go_forward": {
        "category": "browser",
        "risk": "L1",
        "returns_data": True,
        "desc": "浏览器前进",
        "params": {},
    },
    "browser_reload": {
        "category": "browser",
        "risk": "L1",
        "returns_data": True,
        "desc": "刷新当前页面",
        "params": {},
    },
    "browser_evaluate": {
        "category": "browser",
        "risk": "L0",
        "returns_data": True,
        "desc": "在页面执行 JS 脚本",
        "params": {"script": "str"},
    },
    "browser_screenshot": {
        "category": "browser",
        "risk": "L0",
        "returns_data": True,
        "desc": "浏览器页面截图",
        "params": {"selector": "str?", "full_page": "bool=false"},
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
    "move_file": {
        "category": "file",
        "risk": "L2",
        "desc": "移动文件/目录",
        "params": {"src": "str", "dst": "str"},
    },
    "rename_file": {
        "category": "file",
        "risk": "L2",
        "desc": "重命名文件/目录",
        "params": {"path": "str", "new_name": "str"},
    },
    "delete_file": {
        "category": "file",
        "risk": "L2",
        "desc": "删除文件或目录（高风险，需确认）",
        "params": {"path": "str"},
    },
    "search_files": {
        "category": "file",
        "risk": "L0",
        "returns_data": True,
        "desc": "递归搜索文件，支持通配符",
        "params": {"pattern": "str", "path": "str=.", "recursive": "bool=true", "max_results": "int=100"},
    },
    "get_file_info": {
        "category": "file",
        "risk": "L0",
        "returns_data": True,
        "desc": "获取文件详细信息",
        "params": {"path": "str"},
    },
    "ensure_directory": {
        "category": "file",
        "risk": "L1",
        "desc": "确保目录存在，不存在则创建",
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
        "desc": "截屏（全屏/窗口/区域，支持 Base64）",
        "params": {"mode": "fullscreen|active_window|region", "base64": "bool=false", "quality": "int=85"},
    },
    "capture_region": {
        "category": "perception",
        "risk": "L0",
        "returns_data": True,
        "desc": "指定区域截图",
        "params": {"left": "int", "top": "int", "width": "int", "height": "int", "base64": "bool=false"},
    },
    "capture_window": {
        "category": "perception",
        "risk": "L0",
        "returns_data": True,
        "desc": "按标题截取窗口截图（空=前台窗口）",
        "params": {"title": "str?", "base64": "bool=false"},
    },
    "capture_region_interactive": {
        "category": "perception",
        "risk": "L0",
        "returns_data": True,
        "desc": "打开全屏覆盖层，鼠标拖拽选择区域后截图（交互式区域截图）",
        "params": {},
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
