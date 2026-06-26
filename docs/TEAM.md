# 灵枢 SenseHub 团队分工说明（TEAM）

> **文档版本**：v1.1（与 `journal.md` 对齐）  
> **团队规模**：5 人（组长 1 人 + 组员 4 人）  
> **适用**：研发协作、答辩分工说明、进度复盘

---

## 1. 产品矩阵与负责人

| 产品 | 路由 | 主责 | 协责 | 交付要点 |
|------|------|------|------|----------|
| **灵枢 Console** | `/claw` | 组长 + 组员 C | 组员 B、D | 桌面/浏览器执行、工具 trace、多模态感知入口 |
| **灵枢 Studio** | `/studio` | 组员 B | 组员 D | 多模型对话、**Chat Harness**、会话与编排轨迹 |
| **灵枢 Code** | `/code` | 组员 B + 组员 D | 组员 C | 本地 IDE、**Code Harness**、Agent/Plan 双模式 |
| **Token Plan / 运营** | `/token-plan`、`/console/*` | 组长 + 组员 D | 组员 B | 四档订阅、积分钱包、API Key、安全中心 |
| **感知能力** | `/perception/*`、Hub 内嵌 | 组员 A | 组员 D | 摄像头、语音、虚拟屏（Max） |
| **官网与文档** | `/`、`docs/` | 组长 | 全员 | SPEC、TIERS、ARCHITECTURE、SETUP、验收 |

---

## 2. 角色一览

| 角色 | 负责模块 | 主要工作 |
|------|----------|----------|
| **组长** | 架构 · Gateway · Runtime · 安全 · 商业化 · 数据 | 技术方案与接口定义；`gateway/` 会话串行与 `/ws/agent`；`runtime/AgentRuntime` 执行闭环；沙箱 L0–L2、审计、Kill Switch；`licensing/` 四档门控；`db/` 用户/任务/钱包表设计；`docs/` 与集成验收、主线合并 |
| **组员 A** | 感知层 | 摄像头采集与 YOLO 叠框、Whisper/语音指令、手势与虚拟屏校准、感知事件入库、Hub 摄像头/语音 hook |
| **组员 B** | 认知与编排 | `LLMRouter` 多模型路由；意图/规划/应答多脑；`dispatch` 分流；**Console / Chat / Code 三套 Harness**；`studio_models`；`orchestration/` LangGraph 与任务状态机；Token 用量统计 |
| **组员 C** | 执行层 | 工具注册表与 OpenAI FC schema；PyAutoGUI 桌面、Playwright 浏览器；微信/记事本/图片下载等原子链；`generate_document` / `run_document_script`；`gui_agent` 兜底；`skills/bundled/` 规程 Skill |
| **组员 D** | Web 与 API | `sensehub/api/` REST + WebSocket；React 三 Shell（`MimoClaw/Studio/Code/Console`）；`HubPage` / `StudioPage` / `CodePage`；运营与游戏化 UI；双主题、i18n；局域网前端适配 |

---

## 3. 协作关系（三产品线）

```
                    ┌─────────────────────────────────────┐
                    │           组员 D（Web / API）        │
                    │  /claw  /studio  /code  /console/*   │
                    └───────────┬─────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   Console 链路            Studio 链路             Code 链路
          │                     │                     │
          ▼                     ▼                     ▼
   组员 B：意图+            组员 B：Chat           组员 B：Code
   Console Harness          Harness                Harness
          │                     │                     │
          ▼                     │                     ▼
   组长：Gateway +              │              组员 C：文档脚本
   AgentRuntime                 │              （协）本地改码 API
          │                     │                     │
          ▼                     ▼                     ▼
   组员 C：工具执行         用户所选 LLM          edits 回写本地
          ▲
          │
   组员 A：视/听/虚拟屏 ──→ 上下文注入 Hub

组长：接口评审、安全/档位、db、文档、合并 main、阶段验收
```

**要点**

- **Studio / Code 不经过 AgentRuntime 桌面链**，与 Console 硬隔离，由组员 B 的 Harness 独立编排。  
- **Console** 走 `dispatch → gateway → AgentRuntime → 组员 C 工具`。  
- **商业化**（积分、档位、游戏化）由组长定规则与 API，组员 D 做 Console 运营页。

---

## 4. 代码目录归属

| 成员 | 目录与文件（主要） |
|------|-------------------|
| **组长** | `sensehub/gateway/`、`sensehub/runtime/`、`sensehub/security/`、`sensehub/licensing/`、`sensehub/db/`、`sensehub/config/`、`config/*.yaml`、`docs/`、`scripts/start_*.ps1` |
| **组员 A** | `sensehub/perception/`、`sensehub/api/routes/perception.py`、`voice.py`、`virtual_screen.py` |
| **组员 B** | `sensehub/cognition/`（含 `chat_harness.py`、`code_harness.py`、`console_harness.py`、`dispatch.py`、`router.py`、`chat_memory.py`、`studio_models.py`）、`sensehub/orchestration/`、`config/chat_harness.yaml`、`config/console_harness.yaml`、`config/models.yaml` |
| **组员 C** | `sensehub/execution/`、`sensehub/skills/bundled/`、`sensehub/rules/`（动作侧）、`config/skills.yaml` |
| **组员 D** | `sensehub/api/`（除 A 独占路由外）、`sensehub/api/ws*.py`、`web/` 全部 |

---

## 5. 功能清单 × 负责人

### 5.1 Console（执行工作台）

| 功能 | 负责人 |
|------|--------|
| 自然语言多步任务、`/api/hub/command` | 组长 + B + C + D |
| AgentRuntime、Function Calling、工具修复 | 组长 + B |
| 桌面键鼠、窗口、截图 | C |
| Playwright 浏览器 snapshot-act | C |
| 微信/QQ/记事本快捷链 | C |
| 文档/海报/PPT 生成工具 | C |
| Thinking Trace、WebSocket 过程展示 | D |
| Console Harness 策略（IM、文档、登录门控） | B + 组长 |
| 摄像头/语音/虚拟屏 Hub 入口 | A + D |

### 5.2 Studio（对话）

| 功能 | 负责人 |
|------|--------|
| `/api/studio/chat`、多模型选择 | B + D |
| Chat Harness（记忆脑、复杂度路由、质检/精炼） | B |
| 会话 `channel=studio`、Harness 轨迹 UI | B + D |
| Studio 代采模型配置 `studio_models.yaml` | B |

### 5.3 Code（编程 IDE）

| 功能 | 负责人 |
|------|--------|
| `/api/code/assist`、Code Harness | B |
| Agent / Plan 模式、Monaco、本地目录绑定 | D |
| 插件门控（Console 启用 Code Agent） | 组长 + D |

### 5.4 商业化与用户粘性

| 功能 | 负责人 |
|------|--------|
| Lite/Standard/Pro/Max 四档、`TIERS.md` | 组长 |
| 积分钱包、兑换、订阅、账单 | 组长 + D |
| 邀请好友、邀请二维码 | 组长（API）+ D（UI） |
| 成就中心、转盘、排行榜、成就分享卡片 | 组长（`gamification`）+ D（UI） |
| Token 用量、API Key 配置页 | B + D |

### 5.5 安全与基础设施

| 功能 | 负责人 |
|------|--------|
| JWT 登录、用户表 | 组长 + D |
| 沙箱路径、L2 确认 | 组长 |
| 审计日志 | 组长 |
| 局域网访问（5173 代理、policies LAN） | 组长 + D |

---

## 6. 阶段分工（11 日冲刺对照）

| 阶段 | 天数 | 组长 | A | B | C | D |
|------|------|------|---|---|---|---|
| 立项脚手架 | 1 | 架构文档、仓库 | 感知调研 | 路由/意图骨架 | 工具注册表 | React 初始化 |
| 后端基础 | 2 | DB、JWT、沙箱 | 摄像头 Demo | dispatch | 基础桌面工具 | 登录页 |
| 执行扩展 | 3 | 审计规范 | YOLO 预览 | 规划+安全脑 | 浏览器+输入 | Hub 对话区 |
| Runtime | 4 | Gateway+Runtime+WS | 语音骨架 | Console Harness | IM/记事本 | Thinking Trace |
| 三产品线 UI | 5 | 任务账本+Kill Switch | 虚拟屏校准 | 应答脑 | 研究/天气工具 | 三 Shell+主题 |
| Studio | 6 | Studio/Console 隔离 | 感知事件 | Studio API+模型 | 文档生成工具 | Studio 页 |
| Chat Harness | 7 | Harness 文档 | 手势规则草案 | **Chat Harness 全链路** | 图片下载 | Harness Trace |
| Code IDE | 8 | Code 门控 | Max 功能开关 | **Code Harness** | 文档沙箱脚本 | Code 三栏 IDE |
| 商业化 | 9 | TIERS+钱包+档位 | 感知冒烟 | Token 统计 | 工具 schema | Console 运营页 |
| 粘性+联调 | 10 | 局域网说明 | 语音联调 | 内容合成修复 | PPT/文档修复 | 游戏化+邀请/成就分享 |
| 验收交付 | 11 | 冒烟+report | 感知验收项 | Harness 演示素材 | 任务回归 | 构建+走查 |

> 逐日明细与进度百分比见项目根目录 **[journal.md](../journal.md)**。

---

## 7. 协作约定

- **接口变更**：组长评审 → 更新 `docs/ARCHITECTURE.md` → 全员同步  
- **Harness 变更**：组员 B 主笔，须区分 Console / Chat / Code，禁止混用  
- **工具新增**：组员 C 实现并注册，组长确认风险等级，组员 B 更新 planner 可见性  
- **前端路由**：组员 D 维护 `web/src/App.tsx`，新增页面须标明所属产品线  
- **分支命名**：`feat/<角色>-<简述>`，组长合并 `main`  
- **集成节点**：第 4、7、9、11 天全员联调；结束跑 `docs/SMOKE_TESTS.md`  
- **文档**：交付文档放 `docs/`；过程日志放根目录 `journal.md`；答辩架构图见 `report.md`

---

## 8. 交付物检查表（答辩用）

| 类别 | 交付物 | 验收人 |
|------|--------|--------|
| Console | `/claw` 执行、trace、L2 确认、文档/海报任务 | 组长 |
| Studio | `/studio` 多模型、Chat Harness trace | B |
| Code | `/code` 本地项目、Agent/Plan | B + D |
| 感知 | 摄像头预览、语音入口、虚拟屏（Max） | A |
| 商业化 | 四档、积分、Token Plan、邀请二维码 | 组长 + D |
| 粘性 | 成就中心、分享卡片、转盘 | D |
| 文档 | SPEC、TIERS、ARCHITECTURE、SETUP | 组长 |
| 部署 | `start_backend.ps1`、`start_web.ps1`、局域网说明 | 组长 + D |

---

*与 [journal.md](../journal.md) 配套使用：TEAM 为分工总纲，journal 为 11 日过程记录。*
