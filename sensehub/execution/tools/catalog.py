"""工具目录：供规划脑 / 意图脑引用（程序化优先，VLM 兜底）."""

from __future__ import annotations

TOOL_CATALOG: dict[str, dict] = {
    # --- 桌面 / 窗口 ---
    "open_app": {
        "category": "desktop",
        "risk": "L1",
        "returns_data": False,
        "side_effect": "若已在运行则聚焦主窗口，否则启动",
        "desc": "打开并置前（focus 默认 true）；后续 type_text/save 假定已聚焦，直接操作",
        "params": {
            "name": "str",
            "focus": "bool=true",
            "reuse_if_open": "bool=true",
            "startup_wait": "float=1.1",
            "focus_timeout": "float=10.0",
            "settle_wait": "float=0.45",
        },
    },
    "close_app": {
        "category": "desktop",
        "risk": "L1",
        "desc": "置前目标窗口后 Alt+F4 关闭；用 name（notepad/记事本）或 title 匹配，勿臆造中文标题",
        "params": {
            "name": "str?",
            "title": "str?",
            "timeout": "float=6.0",
        },
        "one_of": [["name"], ["title"]],
    },
    "focus_window": {
        "category": "desktop",
        "risk": "L1",
        "desc": "窗口置前",
        "params": {"title": "str", "timeout": "float=6.0", "settle_wait": "float=0.35", "click_center": "bool=false"},
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
        "desc": "向前台输入/粘贴；默认不 refocus，须先 open_app 置前",
        "params": {
            "text": "str",
            "app": "str?",
            "refocus": "false|true=false",
            "pre_wait": "float=0.12",
            "post_wait": "float=0.15",
        },
    },
    "save_notepad": {
        "category": "desktop",
        "risk": "L1",
        "desc": "记事本 Ctrl+S → 粘贴路径 → 回车",
        "params": {"filename": "str=note.txt"},
    },
    "notepad_type_save": {
        "category": "desktop",
        "risk": "L1",
        "desc": "记事本原子操作：open_app 置前 → Ctrl+V 粘贴 → Ctrl+S 保存",
        "params": {"text": "str", "filename": "str=note.txt", "open": "bool=true"},
    },
    "wechat_send_message": {
        "category": "desktop",
        "risk": "L1",
        "desc": "微信原子操作：置前一次 → Ctrl+F 搜联系人 → 进会话 → 粘贴 → 回车发送（后续步骤默认焦点正确）",
        "params": {
            "contact": "str",
            "message": "str",
            "send": "bool=true",
            "open": "bool=false",
            "search_wait": "float=0.9",
            "chat_wait": "float=0.55",
        },
    },
    "press_key": {
        "category": "desktop",
        "risk": "L1",
        "desc": "单键或组合键",
        "params": {"keys": "list[str]?", "key": "str?"},
        "one_of": [["keys"], ["key"]],
    },
    # --- 键鼠坐标 ---
    "click": {"category": "gui", "risk": "L1", "desc": "点击坐标", "params": {"x": "float", "y": "float", "button": "left|right"}},
    "double_click": {"category": "gui", "risk": "L1", "desc": "双击", "params": {"x": "float", "y": "float"}},
    "scroll": {"category": "gui", "risk": "L1", "desc": "滚轮", "params": {"clicks": "int", "x": "float?", "y": "float?"}},
    "hotkey": {
        "category": "gui",
        "risk": "L1",
        "desc": "快捷键；默认发往当前前台（须先 open_app）；可选 app+focus=true 强制置前",
        "params": {"keys": "list[str]", "app": "str?", "focus": "bool=false", "pre_wait": "float=0.12"},
    },
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
    "web_search_results": {
        "category": "research",
        "risk": "L0",
        "returns_data": True,
        "desc": "全网搜索并返回结构化结果（标题/链接/摘要），不打开浏览器窗口",
        "params": {"query": "str", "max_results": "int=8", "source": "duckduckgo|auto=auto"},
    },
    "get_weather": {
        "category": "research",
        "risk": "L0",
        "returns_data": True,
        "desc": "查询城市天气预报（返回结构化数据，供旅游/出行建议引用）",
        "params": {"location": "str", "days": "int=5", "lang": "str=zh"},
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
    "generate_document": {
        "category": "file",
        "risk": "L2",
        "returns_data": True,
        "desc": "用 Python 库生成 docx/xlsx/pptx/txt/csv/md 并保存（相对路径默认落用户保存目录）",
        "params": {
            "path": "str",
            "format": "docx|xlsx|pptx|txt|csv|md",
            "title": "str?",
            "content": "str?",
            "headers": "list?",
            "rows": "list?",
            "slides": "list?",
        },
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


def _example_for_spec(spec: str) -> str:
    raw = str(spec).replace("?", "").strip()
    base = raw.split("=")[0].strip()
    low = base.lower()
    if low.startswith("int"):
        return "1"
    if low.startswith("float"):
        return "0.5"
    if low.startswith("bool"):
        return "true"
    if low.startswith("list"):
        return '["..."]'
    if "|" in base and not any(low.startswith(t) for t in ("int", "float", "bool", "str", "list")):
        first = base.split("|")[0].strip()
        return f'"{first}"'
    return '"..."'


def format_tools_for_planner() -> str:
    lines = [
        "可用工具（tool）按类别。注意 returns_data：true=结果可写入回答，false=仅副作用操作。",
        "复合任务通用链：returns_data 取证 → 据 output 撰写正文 → notepad_type_save/write_file 等 action。",
        "调用规范：tool 参数必须严格匹配 params，禁止虚构字段；不确定时先观察再行动。",
    ]
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
            one_of = m.get("one_of")
            one_of_hint = ""
            if isinstance(one_of, list) and one_of:
                opts = ["/".join(g) for g in one_of if isinstance(g, list) and g]
                if opts:
                    one_of_hint = f" | 约束: 至少满足 {' 或 '.join(opts)}"
            example_parts: list[str] = []
            for key, spec in (m.get("params", {}) or {}).items():
                if "?" in str(spec):
                    continue
                example_parts.append(f'"{key}": {_example_for_spec(str(spec))}')
            example = "{ " + ", ".join(example_parts) + " }" if example_parts else "{}"
            lines.append(
                f"- {t} [{m.get('risk', 'L1')}, {returns}]: {m['desc']} | params: {params} | "
                f"示例 params: {example}{one_of_hint}"
            )
    return "\n".join(lines)
