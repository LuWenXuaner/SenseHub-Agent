# 灵枢 SenseHub Agent

<p align="center">
  <strong>Windows 本地多模态智能体套件</strong><br/>
  感知环境 · 理解意图 · 规划执行 · 安全可控
</p>

---

## 简介

**灵枢 SenseHub Agent** 是面向 Windows 10/11 的企业级多模态智能体平台。系统通过文本、语音与视觉感知用户环境，由大语言模型完成意图理解与任务规划，并自动操控桌面与浏览器；同时提供多模态对话创作与本地编程辅助能力。

典型部署形态为：**本机常驻 Python 后端 + Web 控制台**（默认不暴露公网）。用户可在浏览器中完成智能体对话、任务执行、模型订阅与账户管理。

**核心闭环**：感知（视 / 听 / 屏 / 指令）→ 理解（LLM + 规则）→ 规划 → 执行（桌面 / 网页）→ 反馈（截图 / 状态 / 语音）

---

## 产品矩阵

| 产品 | 路由 | 说明 |
|------|------|------|
| **灵枢 Console** | `/claw` | 智能体工作台：复杂任务执行、桌面与浏览器自动化、Kill Switch 安全管控 |
| **灵枢 Studio** | `/studio` | 多模态对话：创作、问答、附件上下文与模型选择 |
| **灵枢 Code** | `/code` | 本地项目编程助手：Agent / Plan 工作流、Monaco 编辑器 |
| **用户控制台** | `/console` | 账户、积分、Token Plan、API Key、账单与邀请管理 |
| **模型广场** | `/models` | 旗舰模型代采目录与积分定价 |
| **Token Plan** | `/token-plan` | 四档订阅方案与积分兑换 |

---

## 核心能力

### 智能体执行（Console）

- 自然语言多步任务：解析意图、逐步调用工具、事实验收后回复
- 桌面自动化：应用启动、键鼠操作、窗口管理、截图（PyAutoGUI + pywin32）
- 浏览器自动化：Playwright snapshot-act 模式
- 安全门控：L0–L3 风险分级、高风险操作二次确认、Kill Switch 紧急停止
- 运行时 Skill：bundled + workspace 下的 `SKILL.md` 规程注入

### 多模态感知

- 摄像头预览、YOLO 人员/物体检测、手势与场景事件规则
- 流式 ASR 语音输入与 TTS 语音反馈（按档位开放）
- 虚拟屏幕空中点击（**Max** 档位专属）

### 认知与编排

- 多模型路由：intent / planner / coder / vision / safety 分角色配置（`config/models.yaml`）
- AgentRuntime 逐步 Function Calling，失败时 JSON + repair 兜底
- LangGraph 任务状态机：规划 → 确认 → 执行 → 验收 → 报告
- Harness 门禁：桌面须先 observe、IM 须先搜索等策略约束

### 账户与商业化

- Lite / Standard / Pro / Max 四档订阅，积分透明兑换
- 平台代采旗舰模型 API，支持绑定自有 API Key
- 签到、邀请返利、成就与用量账单

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│  Web 前端 (React + Vite + Tailwind)                         │
│  官网 · Console · Studio · Code · 用户控制台                │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST / WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│  FastAPI 网关 (sensehub/api)                                │
│  认证 · 档位门控 · 审计 · /ws/agent 执行事件                │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  Gateway            Cognition           Execution
  (session lane)     (dispatch/router)   (desktop/browser/tools)
        │                  │                  │
        └──────────► AgentRuntime ◄────────────┘
                           │
                    SQLite 持久化
              (sessions · tasks · users · usage)
```

主执行路径：`Hub/语音` → `dispatch.process_user_input` → `gateway.run_agent` → `AgentRuntime` → 工具注册表 → SQLite 会话/任务。

详细设计见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

---

## 订阅档位

对外提供 **Lite · Standard · Pro · Max** 四档套餐；运行时按 **lite / pro / max** 三档生效权限门控。

| 套餐 | 生效档位 | 定位 |
|------|----------|------|
| **Lite** | `lite` | 入门体验，轻量自动化与基础对话 |
| **Standard** | `pro` | 标准专业版，多模态交互与完整 Console |
| **Pro** | `pro` | 专业开发版，更高 Token 配额与编程工具接入 |
| **Max** | `max` | 旗舰全量版，虚拟屏、多脑协作与自主 Agent |

完整权益对照见 [docs/TIERS.md](docs/TIERS.md)。

开发联调可在 `config/local.env` 中设置 `LICENSE_TIER=max` 启用全量功能。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+ · FastAPI · Uvicorn · LangGraph · LangChain Core |
| 前端 | React 18 · TypeScript · Vite 5 · Tailwind CSS · React Router |
| 自动化 | PyAutoGUI · Playwright · pywin32 |
| 感知 | OpenCV · Ultralytics YOLO · MediaPipe（可选）· faster-whisper（可选） |
| 存储 | SQLite（会话、任务、用户、用量） |
| 安全 | JWT 认证 · bcrypt · 沙箱策略 · 审计日志 |

---

## 环境要求

| 软件 | 版本 | 用途 |
|------|------|------|
| Windows | 10 / 11 | 目标运行平台 |
| Python | 3.11+ | 后端运行时 |
| Node.js | 20+ | 前端开发与构建 |
| Git | 2.x | 版本管理 |
| VC++ Redistributable | 最新 | Python 原生依赖 |
| FFmpeg | 4.x+ | 音视频处理（可选） |
| Chromium | Playwright 自带 | 浏览器自动化 |

首次运行前需复制并填写配置模板（见下方「配置说明」）。详细部署步骤见 [docs/SETUP.md](docs/SETUP.md)。

---

## 快速启动

### 1. 首次配置

```powershell
cd "I:\SenseHub Agent"

copy config\local.env.example config\local.env
copy config\paths.yaml.example config\paths.yaml
copy config\models.yaml.example config\models.yaml
copy config\policies.yaml.example config\policies.yaml
```

编辑 `config\local.env`、`config\paths.yaml`、`config\models.yaml`，填写 API Key、数据目录与模型路径。

> **注意**：上述本地配置文件已在 `.gitignore` 中，请勿提交到版本库。

### 2. 启动后端

```powershell
# 方式 A：脚本（推荐，读取 local.env 中的 PYTHON_PATH）
.\scripts\start_backend.ps1

# 方式 B：手动指定 Python
D:\anaconda3\envs\py312\python.exe -m pip install -e .
D:\anaconda3\envs\py312\python.exe -m sensehub.main
```

### 3. 启动前端

**新开一个终端**：

```powershell
# 方式 A：脚本
.\scripts\start_web.ps1

# 方式 B：手动
cd web
npm install    # 首次或依赖变更后
npm run dev
```

### 4. 访问地址

| 用途 | 地址 |
|------|------|
| 前端（开发） | http://127.0.0.1:5173 |
| 后端 API | http://127.0.0.1:8765 |
| Swagger 文档 | http://127.0.0.1:8765/docs |
| 健康检查 | http://127.0.0.1:8765/health |

默认管理员密码见 `config/local.env` 中的 `ADMIN_PASSWORD`。

### 5. 局域网访问

| 项目 | 说明 |
|------|------|
| 访问地址 | `http://<主机局域网 IP>:5173`（**不是** `:8765`） |
| 8765 端口 | 仅后端 API，不提供网页界面 |
| 登录要求 | `/studio`、`/claw`、`/code` 均需登录；每台设备单独登录 |
| 防火墙 | 需放行入站 **TCP 5173**（Vite 开发服务器） |
| 局域网 API | 其他设备直连 `:8765` 时，需在 `config/policies.yaml` 设置 `network.allow_lan: true` |

---

## 配置说明

```
config/
├── local.env.example       → 复制为 local.env（密钥、端口、档位）
├── paths.yaml.example      → 复制为 paths.yaml（数据与模型路径）
├── models.yaml.example     → 复制为 models.yaml（LLM 路由与 API Key）
├── policies.yaml.example   → 复制为 policies.yaml（安全与网络策略）
├── rules.example.yaml      → 自定义规则示例
└── console_brain_catalog.yaml  → Console 多脑路由目录
```

| 配置项 | 说明 |
|--------|------|
| `PYTHON_PATH` | Python 解释器绝对路径 |
| `DATA_ROOT` | SQLite 数据库、截图、录音等数据目录 |
| `MODELS_ROOT` | YOLO、Whisper 等本地模型权重目录 |
| `LICENSE_TIER` | 开发联调档位（lite / pro / max） |
| `ADMIN_PASSWORD` | 首次登录管理员密码 |

---

## 项目结构

```
SenseHub-Agent/
├── config/                     # 运行时配置模板与示例
├── docs/                       # 产品、架构、部署文档
├── scripts/                    # 启动、冒烟测试、部署脚本
├── sensehub/                   # Python 后端
│   ├── api/                    # FastAPI 路由、中间件、WebSocket
│   ├── gateway/                # Agent 控制面、session lane、/ws/agent
│   ├── runtime/                # AgentRuntime、Harness 门禁、事实验收
│   ├── cognition/              # 意图、dispatch、LLM 路由、Harness
│   ├── orchestration/          # LangGraph 状态机、任务 runner
│   ├── execution/              # 工具实现（desktop / browser / file …）
│   ├── perception/             # 摄像头、ASR、虚拟屏、YOLO 检测
│   ├── licensing/              # 订阅档位与用量门控
│   ├── security/               # 认证、沙箱、审计、Kill Switch
│   ├── db/                     # SQLite 数据访问层
│   ├── feedback/               # TTS 与执行反馈钩子
│   ├── rules/                  # 自定义规则引擎
│   └── skills/bundled/         # 内置运行时 Skill（SKILL.md）
├── web/                        # React 前端
│   ├── src/pages/              # 页面（Hub、Studio、Code、Console …）
│   ├── src/components/         # UI 组件（mimo / marketing / hub …）
│   └── src/lib/                # API 客户端、i18n、模型目录
└── SenseHubData/               # 运行时数据（不入库，本地生成）
```

---

## 开发指南

### 安装可选依赖

```powershell
# 语音感知（Phase 2）
pip install -e ".[phase2]"

# TTS 反馈（Phase 3）
pip install -e ".[phase3]"

# 开发工具
pip install -e ".[dev]"
```

### Playwright 浏览器

```powershell
playwright install chromium
```

### 环境验收

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke\run_all.ps1
```

### 前端生产构建

```powershell
cd web
npm run build
# 产物输出至 web/dist/
```

### 密钥扫描（提交前）

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-secrets.ps1
```

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/SPEC.md](docs/SPEC.md) | 产品与技术规格（交付版） |
| [docs/TIERS.md](docs/TIERS.md) | 四档订阅与产品线权益对照 |
| [docs/SETUP.md](docs/SETUP.md) | 环境部署与预配置指南 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构与模块接口 |
| [docs/UI_DESIGN.md](docs/UI_DESIGN.md) | Web 控制台 UI 设计总纲 |
| [docs/SMOKE_TESTS.md](docs/SMOKE_TESTS.md) | 冒烟测试与验收标准 |
| [docs/DEPLOY_ALIYUN.md](docs/DEPLOY_ALIYUN.md) | 阿里云部署指南 |
| [docs/SKILLS.md](docs/SKILLS.md) | Cursor Skill 与运行时 Skill 说明 |
| [启动与提交.md](启动与提交.md) | 本地开发命令速查 |

---

## 版本与许可

| 项 | 说明 |
|----|------|
| 产品版本 | 0.1.0（见 `pyproject.toml`） |
| 规格版本 | 见 [docs/SPEC.md](docs/SPEC.md) 文首 |
| 核心代码 | 计划采用 MIT 许可证 |
| 第三方 | Ultralytics YOLO 遵循 AGPL-3.0，商用部署请注意合规审查 |

---

## 远程仓库

- GitHub：https://github.com/LuWenXuaner/SenseHub-Agent.git

```powershell
git clone https://github.com/LuWenXuaner/SenseHub-Agent.git
cd SenseHub-Agent
copy config\local.env.example config\local.env
# 填写 API Key 与路径后启动
```

---

<p align="center"><em>灵枢 SenseHub — 与你同行，探索智能的温度</em></p>
