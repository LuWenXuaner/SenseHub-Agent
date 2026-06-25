---
id: browser-automation
name: 浏览器自动化规程
description: Playwright snapshot-act 循环；图片搜索下载
tier_min: lite
triggers:
  - browser
  - 网页
  - 网站
  - 浏览器
  - 图片
  - 下载
---

## 规程

### 搜索并下载图片（推荐）

1. 一步：`search_and_download_image(query=关键词)`；用户要「在浏览器里搜」时 `open_browser=true`
2. 分步：`search_images` → 从 `images[].url` 选一张 → `download_image(url=…)`

### Playwright 页面操作

1. `browser_status` 查看浏览器是否就绪
2. `browser_navigate` 打开目标 URL
3. `browser_snapshot` 获取页面结构与 ref
4. `browser_act` 按 ref 操作（click/fill/press）
5. 页面变化后重新 `browser_snapshot`，勿盲操作

## 兜底

- 仅需打开搜索页：`web_search(query=…)`
- snapshot/act 失败可用 `gui_agent`（须先 `web_search` / `open_app` 置前浏览器）
