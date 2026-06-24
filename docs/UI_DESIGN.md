# 灵枢 Agent UI 设计总纲

> 目标：一套 **可扩展** 的控制台界面，从 Phase 1 MVP 到 Phase 4 多模态/分档，**不推翻重做**。  
> 主题：**深色 + 浅色双主题**（用户可切换，跟随系统可选）。  
> 参考：[`skills-example/`](../skills-example/) 中的 `ui-ux-pro-max`、`ui-styling`、`design-system`。

---

## 1. 设计原则

| 原则 | 说明 |
|------|------|
| **顾全大局** | Phase 1 只实现部分页面，但 **信息架构、路由、布局槽位** 按全功能预留 |
| **双主题一等公民** | 所有颜色/阴影/边框用 CSS 变量；禁止组件内硬编码 `#fff` / `#000` |
| **档位可感知** | Lite/Pro/Max 共用同一套 UI；不可用功能 **可见但锁定**，引导升级 |
| **多模态同屏** | 文本、语音、视频、任务状态可在同一 Dashboard 协同，不拆成多个孤立 App |
| **控制台而非落地页** | 信息密度适中、操作路径短；避免花哨全屏动效（参考 `ui-ux-pro-max` 优先级 1–3） |

---

## 2. 信息架构（全 Phase 路由）

Phase 1 只实现「✓」页面，其余用 **占位路由 + TierGate 壳** 保留导航。

```
/                          Dashboard（总览）                    ✓ Phase 1
/command                   指令中心（文本 + 语音入口）         ✓ Phase 1
/tasks                     任务时间线                         ✓ Phase 1
/tasks/:id                 任务详情                           ✓ Phase 1

/perception                感知总览（摄像头/麦克风状态）       ○ Phase 2 壳
/perception/camera         摄像头预览 + 检测框                 Phase 2
/perception/voice          语音识别 / 快捷命令                 Phase 2
/perception/virtual-screen 虚拟屏校准                         ○ Max 锁定

/rules                     规则管理                           ○ Phase 2 壳
/rules/new                 新建规则                           Phase 2

/models                    模型与 API 配置                    ○ Phase 2 简版
/security                  安全中心（会话/白名单/审计）        ○ Phase 3 壳
/settings                  设备、主题、确认策略               ✓ Phase 1 基础
/billing                   档位与用量                         ✓ Phase 1 简版（展示限额）
/login                     登录                               ✓ Phase 1
```

**导航结构**：左侧固定 Sidebar（图标 + 文案），分组：

1. **控制台** — Dashboard、指令、任务  
2. **感知** — 摄像头、语音、虚拟屏（后两项 Phase 2+）  
3. **自动化** — 规则、宏（Phase 2+）  
4. **系统** — 模型、安全、设置、档位  

---

## 3. 布局框架（全页面共用）

```
┌─────────────────────────────────────────────────────────────┐
│ TopBar: Logo「灵枢 Agent」| Agent 状态 | 档位徽章 | 主题切换 | Kill Switch │
├──────────┬──────────────────────────────────────────────────┤
│ Sidebar  │  Main（随路由变化）                               │
│          │  ┌─────────────────────────────────────────────┐ │
│          │  │  PageHeader: 标题 + 描述 + 档位提示（可选）   │ │
│          │  ├─────────────────────────────────────────────┤ │
│          │  │  Content Area                                │ │
│          │  └─────────────────────────────────────────────┘ │
│          │  ┌─ CommandDock（指令/语音，Phase 1 起）──────────┐ │
│          │  │ 文本输入 | 语音按钮 | 快捷命令 | 发送           │ │
│          │  └──────────────────────────────────────────────┘ │
└──────────┴──────────────────────────────────────────────────┘
```

### Phase 2+ Dashboard 多模态区域（预留网格）

```
┌─────────────────┬─────────────────┐
│ 任务状态卡片     │ 今日用量 / 档位   │
├─────────────────┼─────────────────┤
│ 摄像头预览 16:9  │ 语音波形 / ASR   │  ← Phase 2 启用
│ （检测框 overlay）│ 实时字幕         │
├─────────────────┴─────────────────┤
│ 任务时间线（纵向 steps + 截图）       │
└───────────────────────────────────┘
```

Phase 1 Dashboard 右侧/下方用 **占位 Card**（「摄像头 — Phase 2 开放」），保持布局不变。

---

## 4. 双主题 Design Tokens

采用三层 token（参考 `design-system`）：primitive → semantic → component。

### 4.1 Semantic Tokens（`web/src/styles/theme.css`）

| Token | 浅色 | 深色 | 用途 |
|-------|------|------|------|
| `--background` | `#FAFAFA` | `#0F1117` | 页面底 |
| `--surface` | `#FFFFFF` | `#1A1D27` | 卡片 |
| `--surface-elevated` | `#FFFFFF` | `#232734` | 弹层 |
| `--border` | `#E5E7EB` | `#2D3348` | 分割线 |
| `--text-primary` | `#111827` | `#F3F4F6` | 正文 |
| `--text-secondary` | `#6B7280` | `#9CA3AF` | 次要 |
| `--primary` | `#6366F1` | `#818CF8` | 品牌靛蓝 |
| `--success` | `#22C55E` | `#4ADE80` | 成功 |
| `--warning` | `#F59E0B` | `#FBBF24` | 警告 |
| `--danger` | `#EF4444` | `#F87171` | 危险/Kill |
| `--ring` | `#6366F1` | `#818CF8` | 焦点环 |

### 4.2 主题切换

- 存储：`localStorage.theme` = `light` | `dark` | `system`
- 实现：`class="dark"` on `<html>` + Tailwind `darkMode: 'class'`
- 设置页 + TopBar 快捷切换
- 尊重 `prefers-reduced-motion`

### 4.3 字体

- 中文：`"Microsoft YaHei", "PingFang SC", sans-serif`
- 西文/数字：`"Inter", system-ui, sans-serif`（Dashboard 数据表格）
- 基准：`16px`，行高 `1.5`

---

## 5. 档位 UI 策略（Lite / Pro / Max）

**同一应用、同一导航**；差异通过 **TierGate 组件** 表达，不做三套独立界面。

### 5.1 TierGate 行为

| 用户档位 | 功能状态 | UI 表现 |
|----------|----------|---------|
| 有权限 | 可用 | 正常交互 |
| 无权限（低档位） | 锁定 | 卡片/菜单可见 + 锁图标 + 「Pro/Max 可用」+ 升级 CTA |
| 超额（如 Lite 20 次/日） | 限流 | Toast + 用量条变红 + 跳转 `/billing` |

### 5.2 导航与页面可见性

| 导航项 | Lite | Pro | Max |
|--------|------|-----|-----|
| Dashboard / 指令 / 任务 | ✓ | ✓ | ✓ |
| 摄像头预览 | ✓ | ✓ | ✓ |
| 手势 / 场景规则 | 锁定 | ✓ | ✓ |
| 虚拟屏校准 | 锁定 | 锁定 | ✓ |
| 规则数量 | 3 条上限提示 | 50 条 | 无限 |
| 安全中心 / 局域网 | 简版 | 完整 | 完整 + 隧道 |
| 审计导出 | 锁定 | 90 天 | 1 年 + 导出 |

### 5.3 档位徽章（TopBar）

- Lite：灰色 `Lite`
- Pro：靛蓝 `Pro`
- Max：渐变描边 `Max`
- 点击跳转 `/billing`

### 5.4 用量组件（`/billing` 与 Dashboard 卡片）

- 文本指令：今日 `已用/限额` 进度条  
- 语音快捷：已配置条数  
- 规则：已用/上限  
- Phase 1 仅展示文本指令限额，其余 Phase 2+ 追加

---

## 6. 多模态 UI 组件（分阶段启用）

| 组件 | 路径 | Phase | 说明 |
|------|------|-------|------|
| `CommandDock` | 全局底栏 | 1 | 文本 + 语音按钮（Phase 1 语音可 disabled） |
| `TaskTimeline` | /tasks | 1 | 步骤、日志、截图缩略图 |
| `AgentStatusChip` | TopBar | 1 | online / busy / error |
| `KillSwitchButton` | TopBar | 1 | 危险色，二次确认 |
| `CameraPreviewCard` | Dashboard, /perception | 2 | WebSocket JPEG + 检测框 canvas overlay |
| `VoicePanel` | /perception/voice | 2 | 波形、VAD 指示、实时字幕 |
| `RuleEditor` | /rules | 2 | 触发器 + 动作表单 |
| `PlanConfirmDialog` | 全局 | 3 | L2 操作批准计划 |
| `VirtualScreenCalibrator` | /perception/virtual-screen | 4 | 九点校准向导 |
| `TierGate` | 包裹任意功能 | 1 | 统一档位门控 |
| `UpgradePrompt` | 全局 | 1 | 升级引导 Dialog |

### 感知隐私

- 摄像头/麦克风默认 **关闭**；显式「开启感知」Toggle  
- 关闭时预览区显示占位 + 隐私说明  
- 状态同步后端 `policies.yaml`

---

## 7. 关键页面线框说明

### 7.1 Dashboard（Phase 1 可交付）

- 上行：Agent 状态、当前任务、今日指令用量  
- 中行：快捷指令 Chip；Phase 2 左摄像头右语音占位  
- 下行：最近 5 条任务摘要 → 链到 `/tasks`

### 7.2 指令中心 `/command`

- 大文本框 + 历史指令  
- 侧边：结构化命令 `/screenshot` 帮助  
- Phase 2：语音按住说话按钮

### 7.3 任务详情 `/tasks/:id`

- 左侧步骤条（LangGraph 状态）  
- 右侧：每步日志 + 截图 lightbox  
- L2 步骤：黄色「待确认」Banner

### 7.4 设置 `/settings`

- 主题：浅色 / 深色 / 跟随系统  
- 设备：摄像头索引、麦克风（Phase 2）  
- 确认策略：L2 是否弹窗

---

## 8. 技术栈与目录（Phase 1 起）

```
web/
├── src/
│   ├── components/
│   │   ├── layout/       # AppShell, Sidebar, TopBar, CommandDock
│   │   ├── tier/         # TierGate, UpgradePrompt, UsageMeter
│   │   ├── tasks/        # TaskTimeline, StepCard
│   │   ├── perception/   # CameraPreview, VoicePanel（Phase 2）
│   │   └── ui/           # shadcn 组件
│   ├── pages/            # 与路由对应
│   ├── hooks/            # useTheme, useTier, useWebSocket
│   ├── lib/              # api client, tier constants
│   └── styles/
│       └── theme.css     # Design tokens
```

---

## 9. 无障碍与 UX 底线（来自 ui-ux-pro-max）

- 正文对比度 ≥ 4.5:1（双主题均校验）  
- 焦点环可见；键盘可完成核心操作  
- 异步：按钮 loading、骨架屏、WebSocket 断连 Banner  
- 图标按钮必须 `aria-label`  
- 动效 150–300ms；支持 `prefers-reduced-motion`

---

## 10. Phase 与 UI 交付对照

| Phase | UI 交付 |
|-------|---------|
| **1** | AppShell、双主题、Dashboard、指令、任务、登录、Kill Switch、TierGate 壳、billing 用量 |
| **2** | 摄像头预览、语音 Panel、规则页、感知占位替换为实功能 |
| **3** | 安全中心、计划确认 Dialog、局域网提示、完整 billing |
| **4** | 虚拟屏校准、VLM 结果展示、宏管理 |

---

## 11. 待办（后续版本）

- 用户注册 / 多账号体系（当前仅本地主密码登录）
- 登录页邮箱注册或 OAuth

---

## 相关文档

- [档位对照](TIERS.md)
- [产品规格 §2.9](SPEC.md)
- [Cursor Skill：sensehub-ui](../.cursor/skills/sensehub-ui/SKILL.md)
- [外部参考 skills-example/](../skills-example/)
