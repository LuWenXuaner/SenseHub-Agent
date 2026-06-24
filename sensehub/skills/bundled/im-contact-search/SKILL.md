---
id: im-contact-search
name: IM 联系人搜索规程
description: 聊天应用内找人、进会话、再输入
tier_min: lite
triggers:
  - 好友
  - 联系人
  - 会话
  - 微信
  - 钉钉
  - 聊天
---

## 规程

1. 聚焦目标 IM：`open_app` 或 `focus_window`（`open_app` 不重复启动）
2. `active_window` 确认前台
3. 搜索联系人：`hotkey` Ctrl+F（或应用内搜索快捷键）→ `type_text` 输入姓名 → `press_key` Enter
4. 再次 `active_window` 确认进入正确会话
5. `type_text`（`app` 填应用名）输入消息；用户要求不发送则不要按 Enter 发送

## 禁止

- 未搜索直接把联系人名 `type_text` 到未知焦点窗口
