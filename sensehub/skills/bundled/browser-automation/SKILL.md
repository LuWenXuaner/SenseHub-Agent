---
id: browser-automation
name: 浏览器自动化规程
description: Playwright snapshot-act 循环
tier_min: lite
triggers:
  - browser
  - 网页
  - 网站
  - 浏览器
---

## 规程

1. `browser_status` 查看浏览器是否就绪
2. `browser_navigate` 打开目标 URL
3. `browser_snapshot` 获取页面结构与 ref
4. `browser_act` 按 ref 操作（click/fill/press）
5. 页面变化后重新 `browser_snapshot`，勿盲操作

## 兜底

- snapshot/act 失败可用 `gui_agent` 或 `fetch_url`（仅需文本时）
