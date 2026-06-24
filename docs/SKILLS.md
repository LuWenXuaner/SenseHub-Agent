# 灵枢 Agent Cursor Skill 规划（SKILLS）

开发过程中 Cursor Agent 应遵循项目 Skill，避免 UI 与架构风格漂移。

**Phase 1 起**在 [`.cursor/skills/`](../.cursor/skills/) 创建实际 `SKILL.md` 文件。UI 总纲见 **[UI_DESIGN.md](UI_DESIGN.md)**；`sensehub-ui` Skill 已创建。

**UI 偏好（已确认）**：双主题；界面须预留多模态与 Lite/Pro/Max 档位差异；[`skills-example/`](../skills-example/) 作参考且 **保留在仓库中**（不入 `.gitignore`）。

---

## 1. 项目 Skill 一览

| Skill 目录 | 触发场景 | 维护者 |
|-----------|----------|--------|
| `sensehub-ui` | 编写/修改 `web/` | 组员 D |
| `sensehub-agent` | Agent 核心、LangGraph、执行工具 | 组员 B、C |
| `sensehub-llm-router` | 认知层、models.yaml | 组员 B |
| `sensehub-security` | 认证、审计、策略 | 组长 L |
| `sensehub-perception` | 视觉、语音模块 | 组员 A |

---

## 2. sensehub-ui

**何时使用**：修改 React 前端、Dashboard、组件样式。

**完整规范**：见 **[UI_DESIGN.md](UI_DESIGN.md)** 与 **[`.cursor/skills/sensehub-ui/SKILL.md`](../.cursor/skills/sensehub-ui/SKILL.md)**。

**要点摘要**：
- **双主题**：浅色/深色/跟随系统，CSS 变量 + Tailwind `darkMode: 'class'`
- **顾全大局**：Phase 1 即搭好全量路由与布局槽位；摄像头/语音/虚拟屏用占位，Phase 2–4 填入
- **档位 UI**：Lite/Pro/Max 同一应用；`TierGate` 锁定不可用功能（可见 + 升级引导），非隐藏
- **布局**：Sidebar + TopBar + CommandDock；Dashboard 预留 16:9 摄像头 + 语音区
- **参考**：`skills-example/ui-ux-pro-max`、`ui-styling`、`design-system`
- **主色** `#6366F1`；shadcn/ui + Lucide 图标

**禁止**：每档一套界面、硬编码颜色、.async 无 loading、低对比度灰字。

---

## 3. sensehub-agent

**何时使用**：LangGraph 节点、执行工具注册、任务状态。

**约定**：
- 新工具注册到 `sensehub/execution/tools/registry.py`，标注操作级别 L0–L3
- LangGraph 节点单一职责；状态可序列化到 SQLite
- 路径从 `config/paths.yaml` 加载，禁止硬编码 `C:\` / `D:\`
- 执行前检查 `licensing` 档位；执行后写审计日志
- 错误返回用户可读消息 + `trace_id`

**LangGraph 节点链**：`plan` → `confirm` → `execute` → `verify` → `report`

---

## 4. sensehub-llm-router

**何时使用**：修改 `sensehub/cognition/`、`config/models.yaml`。

**约定**：
- 角色：intent / planner / coder / vision / safety
- API Key 只从 `local.env` 经 pydantic-settings 读取
- 实现超时、重试、fallback 链
- Prompt 模板放 `sensehub/cognition/prompts/`，不在代码中硬编码长 Prompt
- 规划输出必须符合 JSON Schema，经 safety 节点审查

---

## 5. sensehub-security

**何时使用**：认证、策略、审计、Kill Switch。

**约定**：
- 默认绑定 `127.0.0.1`；局域网需 `policies.yaml` 显式开启
- 文件操作限制 `file_whitelist_dirs`
- 维护 `command_blacklist`
- Kill Switch 必须能立即停止 PyAutoGUI 与 Playwright
- 审计字段：timestamp、user、input、action、risk_level、result、trace_id

---

## 6. sensehub-perception

**何时使用**：摄像头、YOLO、ASR、手势。

**约定**：
- 模型路径从 `paths.yaml` 的 `models` 段读取
- 摄像头/麦克风默认关闭，启动需用户授权
- 目标：720p 检测 <200ms/帧（GPU）
- 输出统一 `PerceptionEvent` 结构（见 [ARCHITECTURE.md](ARCHITECTURE.md)）
- 视频帧默认不上传；仅 vision LLM 调用时发送

---

## 7. 目录结构（Phase 1 创建）

```
.cursor/skills/
├── sensehub-ui/SKILL.md          ← 已创建
├── sensehub-agent/SKILL.md       Phase 1
├── sensehub-llm-router/SKILL.md  Phase 1
├── sensehub-security/SKILL.md    Phase 1
└── sensehub-perception/SKILL.md  Phase 1
```

每个 Skill 遵循 Cursor 规范：YAML frontmatter（name、description）+ 正文指令。

---

## 8. 运行时 Skills 与 Cursor Skills 区分

| 类型 | 路径 | 用途 |
|------|------|------|
| **运行时 Skill** | `sensehub/skills/bundled/*/SKILL.md` | Agent 执行时注入规程（desktop / IM / browser） |
| **Cursor Skill** | `.cursor/skills/*/SKILL.md` | 仅指导 Cursor 写代码，不参与 Agent |

运行时配置：`config/skills.yaml` 的 `enabled` 列表。

内置规程：

- `desktop-automation` — observe → verify → act
- `im-contact-search` — 先搜索再输入
- `browser-automation` — Playwright snapshot-act 循环

新增运行时 Skill：在 `sensehub/skills/bundled/<id>/SKILL.md` 添加 frontmatter（`id`, `triggers`, `tier_min`），并加入 `config/skills.yaml`。

---

## 相关文档

- [架构与接口](ARCHITECTURE.md)
- [成员分工](TEAM.md)
- [UI 设计总纲](UI_DESIGN.md)
