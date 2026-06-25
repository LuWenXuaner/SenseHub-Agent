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
2. `active_window` 确认前台；若标题含「登录/扫码」→ **停止**，提示用户先自行登录
3. **微信**找人发消息（默认已登录）：优先 `wechat_send_message(contact=姓名, message=内容)` 一步完成
4. 若需分步：`hotkey` `app=微信` `keys=[ctrl,f]` → `type_text` 输入姓名 → `press_key` Enter → `type_text` 输入消息 → 需要发送时再 Enter
5. 再次 `active_window` 确认进入正确会话（分步流程时）
6. 用户要求不发送则 `wechat_send_message` 设 `send=false`，或分步时不要按 Enter 发送

## 禁止

- 代替用户输入密码、验证码或完成扫码登录
- 未搜索直接把联系人名 `type_text` 到未知焦点窗口
