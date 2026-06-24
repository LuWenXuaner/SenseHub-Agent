# 灵枢 Agent（SenseHub Agent）

Windows 本地多模态感知 Agent：通过文本、语音、视频感知环境，利用大模型规划任务，自动操控桌面与浏览器。

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/SPEC.md](docs/SPEC.md) | 产品与技术规格 |
| [docs/SETUP.md](docs/SETUP.md) | **环境预配置指南**（安装软件、模型、填路径） |
| [docs/SMOKE_TESTS.md](docs/SMOKE_TESTS.md) | 分阶段冒烟测试与验收标准 |
| [docs/TIERS.md](docs/TIERS.md) | Lite / Pro / Max 档位对照 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 架构与模块接口 |
| [docs/TEAM.md](docs/TEAM.md) | 成员分工（组长 + 4 组员） |
| [docs/UI_DESIGN.md](docs/UI_DESIGN.md) | **UI 总纲**：双主题、多模态布局、档位 UI |
| [docs/SKILLS.md](docs/SKILLS.md) | Cursor Skill 规划 |

## 环境就绪检查表

开发前请完成：

- [ ] 安装 Python 3.11+、Node 20+、Git、FFmpeg、VC++ Redistributable
- [ ] 创建 `MODELS_ROOT`、`DATA_ROOT` 目录
- [ ] 下载 YOLO、Whisper 等模型权重
- [ ] 申请 LLM API Key
- [ ] 复制并填写 `config/local.env`、`config/paths.yaml`、`config/models.yaml`
- [ ] 允许 Windows 摄像头、麦克风、屏幕录制权限
- [ ] 运行 `scripts\smoke\run_all.ps1` 验收环境
- [ ] 告知 Agent：「环境已就绪」

详细步骤见 [docs/SETUP.md](docs/SETUP.md)。

## 配置模板

```
config/
├── local.env.example      → 复制为 local.env（不入 git）
├── paths.yaml.example     → 复制为 paths.yaml
├── models.yaml.example    → 复制为 models.yaml
├── policies.yaml.example
└── rules.example.yaml
```

## 项目结构

```
SenseHub-Agent/
├── config/
│   ├── skills.yaml          # 运行时 Skill 启用列表
│   ├── models.yaml
│   └── local.env
├── docs/
├── sensehub/
│   ├── gateway/             # Gateway 控制面 + /ws/agent
│   ├── runtime/             # AgentRuntime 单路径执行
│   ├── skills/bundled/      # 运行时 SKILL.md
│   ├── cognition/           # 意图、dispatch、router、repair
│   ├── execution/           # 工具 + browser/playwright
│   ├── db/sessions.py       # 会话 SQLite
│   └── perception/          # 摄像头、虚拟屏、ASR
├── web/                     # React Hub（布局见 UI_DESIGN.md）
└── .cursor/skills/          # Cursor 开发用 Skill（非运行时）
```

## 快速启动

**默认登录密码**：`config/local.env` 中 `ADMIN_PASSWORD`（默认 `sensehub`）

**档位**：`LICENSE_TIER` = `lite` | `pro` | `max`（Pro 解锁流式 ASR/手势/TTS/局域网；Max 解锁虚拟屏/多 Agent）

```powershell
# 终端 1 — 后端 API
cd "I:\SenseHub Agent"
.\scripts\start_backend.ps1

# 终端 2 — 前端控制台
.\scripts\start_web.ps1
```

浏览器打开 http://127.0.0.1:5173 ，登录后可：

- 发送「截个图」「打开记事本」「打开浏览器搜索 xxx」
- 摄像头人员检测、语音指令、规则自动化
- 安全中心（Pro）、虚拟屏校准（Max）
- 查看任务进度与截图
- 切换浅色/深色主题
- 查看 Lite 档位用量

API 文档：http://127.0.0.1:8765/docs

## 开发阶段

| 阶段 | 内容 |
|------|------|
| Phase 0 | 规格文档、环境验收 | 完成 |
| Phase 1 | 文本指令 MVP + Web UI | 完成 |
| Phase 2 | 视觉 + 语音 + 规则 + VLM GUI | 完成 |
| Phase 3 | Pro：流式 ASR、手势、TTS、局域网、安全中心 | **完成** |
| Phase 4 | Max：虚拟屏、多 Agent、安全隧道占位 | **完成** |
| Phase 5 | Gateway + Runtime + Skills + Playwright + 服务端会话 | **完成** |

## 许可证

核心代码计划 MIT；YOLO（Ultralytics）为 AGPL-3.0，商用请注意合规。
