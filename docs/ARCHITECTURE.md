# 灵枢 SenseHub 系统架构说明（ARCHITECTURE）

> **文档版本**：v1.0（商业化交付版）  
> **档位门控**：见 [TIERS.md](TIERS.md)；运行时特性由 `sensehub/licensing/tier.py` 统一校验。

模块划分、数据流与核心接口说明。接口变更须经过评审并同步文档。

---

## 1. 系统分层（OpenClaw 风格 Gateway + 多模态）

```mermaid
flowchart TB
  subgraph ui [交互层 web + api]
    Hub[HubPage / 语音]
    WS[/ws/agent 执行事件]
  end

  subgraph gw [Gateway sensehub/gateway]
    Lane[Session Lane 串行]
    AgentSvc[agent_service.run_agent]
  end

  subgraph rt [Runtime sensehub/runtime]
    Loop[AgentRuntime 逐步 FC/JSON]
    Harness[harness_runtime 门禁]
    Skills[skills 规程注入]
    Verify[verifier 事实验收]
  end

  subgraph cog [认知层 sensehub/cognition]
    Intent[意图脑]
    Router[LLM Router + tool repair]
    Dispatch[dispatch 分流]
  end

  subgraph exec [执行层]
    Desktop[desktop.py Windows]
    Browser[Playwright snapshot-act]
    Vision[gui_agent VLM 兜底]
    Perception[摄像头 / 虚拟屏]
  end

  subgraph state [SQLite]
    Sessions[sessions + messages]
    Tasks[tasks]
  end

  Hub --> Dispatch
  Dispatch -->|execute| AgentSvc
  AgentSvc --> Lane --> Loop
  Loop --> Harness --> exec
  Loop --> Verify
  Skills --> Loop
  AgentSvc --> Sessions
  Loop --> WS
  Intent --> Dispatch
```

**主路径**：`Hub/语音` → `dispatch.process_user_input` → `gateway.run_agent` → `AgentRuntime` → 工具注册表 → SQLite 会话/任务。

**不再推荐**：Hub 同步执行后再走 `orchestrate_brains` 双轨；`run_task(plan=None)` 与自主模式均已统一为 `AgentRuntime`。

---

## 2. 目录与职责

| 目录 | 职责 |
|------|------|
| `sensehub/gateway/` | 控制面：`run_agent`、session lane、`/ws/agent` 事件 |
| `sensehub/runtime/` | `AgentRuntime`、Harness 门禁、桌面事实验收、多模态提示 |
| `sensehub/skills/` | **运行时** `SKILL.md`（bundled + workspace） |
| `sensehub/cognition/` | 意图脑、dispatch、router（含原生 FC）、tool_call_repair |
| `sensehub/execution/` | 工具实现；`browser/playwright_browser.py` snapshot-act |
| `sensehub/db/sessions.py` | 会话 transcript SQLite |
| `sensehub/perception/` | 摄像头、虚拟屏、ASR |
| `sensehub/licensing/` | 订阅档位、用量限额、`feature_enabled` 门控 |
| `sensehub/orchestration/` | LangGraph 确认门、任务 runner、多 Agent 协调 |
| `web/` | React 控制台：Console / Studio / Code / Token Plan |
| `.cursor/skills/` | **开发用** Cursor Skill（不参与运行时） |

---

## 3. Agent 循环

1. 意图脑 JSON → Harness 路由（answer / execute / status / cancel）
2. `execute` → `gateway.run_agent(session_id, text)`
3. 匹配运行时 Skills 注入 system prompt
4. 每轮：原生 **function calling**（失败则 JSON + repair）→ 单工具执行
5. Harness 门禁：桌面须先 observe；IM 找人须先搜索
6. `finish` 前桌面任务 `active_window` + **事实验收**（不采信 LLM 乐观文案）
7. 消息写入 `messages` 表；工具事件推送 `/ws/agent`

---

## 4. 工具分层

| 链 | 工具 | 场景 |
|----|------|------|
| 桌面 | `list_windows`, `active_window`, `open_app`, `hotkey`, `type_text` | Windows 本机 |
| 浏览器 | `browser_navigate`, `browser_snapshot`, `browser_act` | Playwright snapshot-act |
| 研究 | `fetch_url`, `get_weather` | 应答脑数据 |
| 兜底 | `gui_agent` | 复杂 UI / 坐标 VLM |
| 多模态 Max | `virtual_screen_*` + 手势 WS | 虚拟屏点击 |

`open_app`：检测已运行实例（含进程名），不重复启动；聚焦时跳过登录窗。

---

## 5. 会话与任务

- **sessions**：`session_id`, `title`, `user_id`, `updated_at`
- **messages**：`role`, `content`, `meta_json`, 可选 `task_id`
- **tasks**：执行账本；`session_id` 列关联会话
- 前端 `HubPage` 启动时 `GET /api/sessions` 同步；localStorage 作离线缓存

---

## 6. API 入口

| 路径 | 说明 |
|------|------|
| `POST /api/hub/command` | 主控制台（`session_id` + `history`） |
| `GET/POST/DELETE /api/sessions` | 会话 CRUD |
| `POST /api/voice/run` | 语音文本（同 Gateway） |
| `WS /ws/agent` | 执行过程 `tool_start` / `tool_end` |
| `WS /ws/tasks` | 任务状态 |

---

## 7. 配置

| 文件 | 说明 |
|------|------|
| `config/models.yaml` | LLM 角色与 provider |
| `config/skills.yaml` | 启用的运行时 Skill id 列表 |
| `config/paths.yaml` | 工作区、模型路径 |

Playwright 首次使用：`playwright install chromium`

---

## 相关文档

- [运行时 Skills](SKILLS.md#8-运行时-skills-与-cursor-skills-区分)
- [UI 设计总纲](UI_DESIGN.md)
- [档位对照](TIERS.md)
