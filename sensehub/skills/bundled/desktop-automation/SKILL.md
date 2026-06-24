---
id: desktop-automation
name: 桌面自动化规程
description: Windows 桌面 observe-verify-act 通用流程
tier_min: lite
triggers:
  - desktop
  - desktop_action
  - 打开
  - 窗口
---

## 规程

1. 每轮新目标先 `list_windows` 或 `active_window`，勿假定历史里应用仍打开
2. 需要操作某应用时 `open_app`（已运行则聚焦）或 `focus_window`
3. 输入前核对 `active_window`；`type_text` 带 `app` 参数
4. `finish` 前再 `active_window`；只陈述工具返回已验证的事实

## 禁止

- 未观察界面直接 `type_text` / `hotkey`
- 在答复中声称未经验证的成功
