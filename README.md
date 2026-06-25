# 灵枢 SenseHub Agent

**灵枢 SenseHub** 是面向 Windows 平台的企业级多模态智能体套件：通过文本、语音与视觉感知环境，由大模型规划并执行任务，自动操控桌面与浏览器，并提供对话创作与本地编程辅助能力。

---

## 产品矩阵

| 产品 | 路径 | 说明 |
|------|------|------|
| **灵枢 Console** | `/claw` | 智能体工作台：复杂任务执行、桌面与浏览器自动化 |
| **灵枢 Studio** | `/studio` | 多模态对话：创作、问答与模型服务 |
| **灵枢 Code** | `/code` | 本地项目编程助手：Agent / Plan 工作流与 Monaco 编辑 |
| **Token Plan** | `/token-plan` | 积分订阅与旗舰模型代采服务 |

---

## 订阅档位

对外提供 **Lite · Standard · Pro · Max** 四档套餐；运行时按 **lite / pro / max** 三档生效权限门控。完整对照见 **[docs/TIERS.md](docs/TIERS.md)**。

| 套餐 | 生效档位 | 一句话定位 |
|------|----------|------------|
| Lite | lite | 入门体验，适合本地试用与轻量自动化 |
| Standard | pro | 标准专业版，多模态交互与完整 Console 能力 |
| Pro | pro | 专业开发版，更高 Token 配额与编程工具接入 |
| Max | max | 旗舰全量版，虚拟屏、多脑协作与自主 Agent |

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/SPEC.md](docs/SPEC.md) | 产品与技术规格（交付版） |
| [docs/TIERS.md](docs/TIERS.md) | **四档订阅与产品线权益对照** |
| [docs/SETUP.md](docs/SETUP.md) | 环境部署与预配置指南 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构与模块接口 |
| [docs/UI_DESIGN.md](docs/UI_DESIGN.md) | Web 控制台 UI 设计总纲 |
| [docs/SMOKE_TESTS.md](docs/SMOKE_TESTS.md) | 冒烟测试与验收标准 |
| [docs/DEPLOY_ALIYUN.md](docs/DEPLOY_ALIYUN.md) | 阿里云部署指南 |
| [docs/SKILLS.md](docs/SKILLS.md) | Cursor Skill 与运行时 Skill 说明 |
| [docs/TEAM.md](docs/TEAM.md) | 团队分工（内部参考） |

---

## 环境要求

部署前请确认：

- Python 3.11+、Node.js 20+、Git、FFmpeg、VC++ Redistributable
- 配置 `config/local.env`、`config/paths.yaml`、`config/models.yaml`
- 模型权重目录（YOLO、Whisper 等）与数据目录（`DATA_ROOT`）
- Windows 摄像头、麦克风、屏幕录制权限（多模态功能）
- 运行 `scripts\smoke\run_all.ps1` 完成环境验收

详细步骤见 [docs/SETUP.md](docs/SETUP.md)。

---

## 配置模板

```
config/
├── local.env.example      → 复制为 local.env（不入版本库）
├── paths.yaml.example     → 复制为 paths.yaml
├── models.yaml.example    → 复制为 models.yaml
├── policies.yaml.example
└── rules.example.yaml
```

---

## 项目结构

```
SenseHub-Agent/
├── config/                 # 运行时配置
├── docs/                   # 交付文档
├── sensehub/
│   ├── gateway/            # Gateway 控制面
│   ├── runtime/            # AgentRuntime 执行引擎
│   ├── cognition/          # 意图、路由、Harness
│   ├── execution/          # 工具与浏览器自动化
│   ├── perception/         # 摄像头、语音、虚拟屏
│   ├── licensing/          # 档位与用量门控
│   ├── security/           # 沙箱、审计、认证
│   └── skills/bundled/     # 运行时 Skill
├── web/                    # React 控制台与官网
└── scripts/                # 启动与冒烟脚本
```

---

## 快速启动

默认管理员密码见 `config/local.env` 中 `ADMIN_PASSWORD`。

开发环境可通过 `LICENSE_TIER=max` 启用全量功能联调。

```powershell
# 终端 1 — 后端 API
.\scripts\start_backend.ps1

# 终端 2 — 前端
.\scripts\start_web.ps1
```

- 控制台：http://127.0.0.1:5173  
- API 文档：http://127.0.0.1:8765/docs  

### 局域网访问（其他设备）

| 项目 | 说明 |
|------|------|
| **正确地址** | `http://<主机局域网IP>:5173`（例如 `http://10.x.x.x:5173`），**不是** `:8765` |
| **8765 端口** | 仅后端 API，不提供网页界面；直接访问 `/studio`、`/claw` 会失败 |
| **须先登录** | Chat（`/studio`）、Console（`/claw`）、Code（`/code`）均需登录；每台设备单独登录一次 |
| **防火墙** | Windows 需放行入站 **TCP 5173**（开发环境 Vite） |
| **局域网模式** | 若其他设备直连 `:8765` 调 API，需在 `config/policies.yaml` 中设置 `network.allow_lan: true`（示例见 `policies.yaml.example`） |

---

## 版本与许可

- 产品规格版本：见 [docs/SPEC.md](docs/SPEC.md) 文首  
- 核心代码：计划采用 MIT 许可证  
- 第三方：YOLO（Ultralytics）遵循 AGPL-3.0，商用部署请注意合规审查  

---

*灵枢 SenseHub — 与你同行，探索智能的温度*
