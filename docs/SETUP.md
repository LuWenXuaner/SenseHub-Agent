# 灵枢 SenseHub 环境部署与预配置指南（SETUP）

> **文档版本**：v1.0（商业化交付版）  
> **适用对象**：运维人员、交付工程师、本地开发环境搭建

部署或开发前，请在本机完成下列软件安装与配置。配置完成后运行 [SMOKE_TESTS.md](SMOKE_TESTS.md) 中的验收项，确保服务可正常启动。

---

## 1. 快速开始

```powershell
# 1. 复制配置模板
copy config\local.env.example config\local.env
copy config\paths.yaml.example config\paths.yaml
copy config\models.yaml.example config\models.yaml

# 2. 编辑上述三个文件，填写绝对路径与 API Key

# 3. 创建数据与模型目录（按你填写的路径）
mkdir D:\SenseHubData\db, D:\SenseHubData\screenshots, D:\Models\SenseHub

# 4. 环境验收（Phase 1 开发前实现脚本）
# scripts\smoke\run_all.ps1
```

配置完成后告知 Agent：**「环境已就绪，`local.env` 和 `paths.yaml` 已填好」**。

---

## 2. 路径配置汇总

| 配置项 | 环境变量 / YAML 键 | 示例 | 说明 |
|--------|-------------------|------|------|
| Python 解释器 | `PYTHON_PATH` | `I:\SenseHub Agent\.venv\Scripts\python.exe` | 3.11+ |
| 项目 venv | `VENV_PATH` | `I:\SenseHub Agent\.venv` | pip 安装目标 |
| Node.js | `NODE_PATH` | `C:\Program Files\nodejs\node.exe` | 20+ |
| 项目根目录 | `SENSEHUB_ROOT` | `I:\SenseHub Agent` | 工作区 |
| 模型权重根目录 | `MODELS_ROOT` | `D:\Models\SenseHub` | 本地模型 |
| 数据/日志目录 | `DATA_ROOT` | `D:\SenseHubData` | DB、截图、录音 |
| CUDA（可选） | `CUDA_PATH` | `C:\Program Files\NVIDIA...\CUDA\v12.x` | GPU 加速 |

完整模板：[`config/paths.yaml.example`](../config/paths.yaml.example)

---

## 3. 运行时软件

| 软件 | 最低版本 | 用途 | 配置项 |
|------|----------|------|--------|
| Windows | 10/11 | 目标平台 | — |
| Python | 3.11+ | 后端 | `PYTHON_PATH` / venv |
| Node.js | 20+ | 前端构建 | `NODE_PATH` |
| Git | 2.x | 版本管理 | PATH |
| VC++ Redistributable | 最新 | 原生库 | 安装即可 |
| FFmpeg | 4.x+ | 音视频 | `FFMPEG_PATH` |
| Tesseract（可选） | 5.x | OCR | `TESSERACT_PATH` |
| Chromium | Playwright 自带 | 网页自动化 | `playwright install chromium` |
| mkcert（可选） | — | 局域网 HTTPS | `TLS_CERT_DIR` |

### Python 虚拟环境

```powershell
cd "I:\SenseHub Agent"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# Phase 1 起：pip install -e .
```

### Playwright 浏览器

```powershell
.\.venv\Scripts\playwright install chromium
```

---

## 4. 数据库

| 数据库 | 角色 | v1 方案 | 配置键 |
|--------|------|---------|--------|
| **SQLite** | 任务状态、checkpoint、审计 | **默认**，文件在 `DATA_ROOT/db/` | `SQLITE_PATH` |
| Redis（可选） | 会话、pub/sub | Phase 3+ | `REDIS_URL` |
| PostgreSQL（可选） | 大规模审计 | 远期 | `DATABASE_URL` |

v1 只需创建 `DATA_ROOT` 目录，无需独立数据库服务。

---

## 5. 本地模型权重

下载到 `MODELS_ROOT`，并在 `paths.yaml` 中填写绝对路径：

| 模型 | 建议文件 | YAML 键 | 用途 | 档位 |
|------|----------|---------|------|------|
| YOLOv8n / YOLO11n | `yolov8n.pt` | `yolo_weights` | 人体/物体检测 | Lite+ |
| YOLO Pose | `yolov8n-pose.pt` | `yolo_pose_weights` | 姿态 | Pro+ |
| Whisper | `ggml-small.bin` 等 | `whisper_model` | ASR | Lite=small, Max=large |
| Silero VAD | `silero_vad.onnx` | `vad_model` | 语音活动检测 | Pro+ |
| FunASR | Paraformer 目录 | `funasr_model_dir` | 中文流式 ASR | Max |
| MediaPipe Hands | pip 自带 | — | 手部追踪 | Pro+ |

### 下载来源

| 模型 | 来源 |
|------|------|
| YOLO | https://github.com/ultralytics/assets/releases |
| Whisper (ggml) | https://huggingface.co/ggerganov/whisper.cpp |
| faster-whisper | 首次运行可自动下载，或手动指定目录 |
| Silero VAD | https://github.com/snakers4/silero-vad |
| FunASR | https://github.com/modelscope/FunASR |

---

## 6. LLM API 配置

至少配置 **1 个提供商** 即可跑通 MVP；建议配齐 intent / planner / vision 角色。

| 角色 | 职责 | 推荐模型 |
|------|------|----------|
| intent | 分类、实体提取 | gpt-4o-mini / deepseek-chat / qwen-turbo |
| planner | 多步计划 JSON | gpt-4o / claude-sonnet / deepseek-reasoner |
| coder | 选择器、脚本 | gpt-4o / deepseek-coder |
| vision | 截图描述 | gpt-4o / qwen-vl-max / gemini-2.0-flash |
| safety | 拦截危险计划 | 与 intent 同档小模型 |

### API Key 填写

编辑 `config/local.env`（模板：[`local.env.example`](../config/local.env.example)）：

- OpenAI：`OPENAI_API_KEY`、`OPENAI_BASE_URL`
- Anthropic：`ANTHROPIC_API_KEY`
- DeepSeek：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`
- 通义：`DASHSCOPE_API_KEY`
- Gemini：`GEMINI_API_KEY`
- Ollama（本地）：`OLLAMA_BASE_URL=http://127.0.0.1:11434`

### 模型角色映射

编辑 `config/models.yaml`（模板：[`models.yaml.example`](../config/models.yaml.example)）。

---

## 7. Python / Node 依赖

### Python 核心包（Phase 1 写入 pyproject.toml）

- 感知：`opencv-python`, `ultralytics`, `mediapipe`, `faster-whisper`, `silero-vad`
- 认知：`langgraph`, `langchain-core`, `langchain-openai`, `langchain-anthropic`, `httpx`
- 执行：`pyautogui`, `pywin32`, `playwright`, `mss`, `pyperclip`
- 服务：`fastapi`, `uvicorn[standard]`, `websockets`, `python-multipart`
- 安全：`python-jose`, `passlib`, `cryptography`
- 工具：`pyyaml`, `pydantic-settings`, `structlog`, `apscheduler`

### Node 前端包（Phase 1 写入 web/package.json）

`react`, `vite`, `tailwindcss`, shadcn/ui, `@tanstack/react-query`, `socket.io-client`

---

## 8. 硬件与设备

| 配置项 | 环境变量 | 说明 |
|--------|----------|------|
| 摄像头索引 | `CAMERA_INDEX` | 默认 `0` |
| 麦克风设备名 | `MIC_DEVICE_NAME` | 与系统录音设备名称一致 |
| GPU | `USE_CUDA` | `true` / `false` |
| TTS 音色 | `TTS_VOICE` | 如 `zh-CN-XiaoxiaoNeural` |

### Windows 隐私权限

设置 → 隐私 → 开启：
- 摄像头
- 麦克风
- 屏幕截图/录制（供自动化与截图）

---

## 9. 开发前检查表

- [ ] 安装 Python 3.11+、Node 20+、Git、FFmpeg、VC++ Redistributable
- [ ] 创建 `MODELS_ROOT`、`DATA_ROOT` 目录
- [ ] 下载 YOLO、Whisper（及可选 FunASR、Silero VAD）权重
- [ ] 申请至少 1 个 LLM API Key
- [ ] 复制并填写 `local.env`、`paths.yaml`、`models.yaml`
- [ ] 允许 Windows 摄像头、麦克风、屏幕录制权限
- [ ] （可选）Redis、PostgreSQL、CUDA、Tesseract、mkcert
- [ ] 运行 Phase 0 冒烟测试（见 [SMOKE_TESTS.md](SMOKE_TESTS.md)）
- [ ] 告知 Agent 环境已就绪

---

## 相关文档

- [产品规格](SPEC.md)
- [冒烟测试](SMOKE_TESTS.md)
- [架构与接口](ARCHITECTURE.md)
