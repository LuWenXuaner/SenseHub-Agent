---

id: desktop-automation

name: 桌面自动化规程

description: Windows 桌面 open → act 流程

tier_min: lite

triggers:

  - desktop

  - desktop_action

  - 打开

  - 窗口

---



## 规程



1. **open_app(focus=true)**：打开并置前目标软件（唯一需要抢焦点的步骤）

2. 后续 **默认已聚焦**：直接 `type_text` 粘贴、`save_notepad` 保存、`hotkey` 快捷键

3. 记事本「输入并保存」：`open_app` → `type_text` → `save_notepad` 三步连续执行

4. 不要插入 `list_windows` / `active_window` 等多余观察



## 禁止



- open_app 之后反复确认前台或 refocus

- 仅观察就 `agent_finish`

