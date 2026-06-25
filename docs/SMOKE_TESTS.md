# 灵枢 SenseHub 冒烟测试与验收标准（SMOKE_TESTS）

> **文档版本**：v1.0（商业化交付版）

环境配置完成后，**按顺序**执行下列测试。Phase 0 全绿后方可进行功能验收与交付签收。

统一入口（Phase 1 起实现）：

```
scripts/smoke/
├── test_env.py          # E01–E15
├── test_llm.py          # E12–E13
├── test_perception.py   # E06–E11
└── run_all.ps1          # Windows 一键 Phase 0
```

对 Agent 说：「请运行 `scripts/smoke/run_all.ps1` 验收环境」。

---

## Phase 0 — 环境验收

| # | 测试项 | 操作 | 通过标准 | 失败排查 |
|---|--------|------|----------|----------|
| E01 | Python venv | `"%VENV_PATH%\Scripts\python" --version` | 3.11+ | 检查 venv 路径、是否激活 |
| E02 | Node | `node --version` | v20+ | 安装 Node 或修正 PATH |
| E03 | 配置文件 | 存在 `config/local.env` 与 `config/paths.yaml` | 必填项非空 | 复制 example 并填写 |
| E04 | 数据目录 | 在 `DATA_ROOT` 创建测试文件 | 读写成功 | 创建目录、检查权限 |
| E05 | GPU（可选） | `python -c "import torch; print(torch.cuda.is_available())"` | True 或跳过 | 安装 CUDA 版 torch |
| E06 | 摄像头 | OpenCV 打开 `CAMERA_INDEX` 读 1 帧 | 非空帧 | 权限、设备索引、占用 |
| E07 | 麦克风 | 录制 3 秒 wav | 文件 > 0 | 权限、设备名 |
| E08 | FFmpeg | `ffmpeg -version` | 正常输出 | 安装 FFmpeg 并填路径 |
| E09 | Playwright | `playwright install chromium` + 打开 about:blank | 浏览器启动 | 重装 chromium |
| E10 | YOLO | 加载 `YOLO_WEIGHTS` 推理测试图 | 返回检测框 | 权重路径、ultralytics |
| E11 | Whisper | faster-whisper 转写 5 秒音频 | 输出文本 | 模型路径、FFmpeg |
| E12 | LLM API | intent 角色发送「你好」 | 200、<5s | Key、网络、models.yaml |
| E13 | LLM 路由 | planner、vision 各测 1 次 | 均成功 | 角色映射、配额 |
| E14 | SQLite | 建表插入查询 | 无错误 | 路径、目录权限 |
| E15 | Redis（可选） | `PING` | `PONG` | 服务是否启动 |

---

## Phase 1 — MVP 功能冒烟

| # | 测试项 | 操作 | 通过标准 |
|---|--------|------|----------|
| M01 | Agent 启动 | 启动 FastAPI | `GET /health` 返回 ok |
| M02 | Web UI | 打开控制台 | 渲染正常、无报错 |
| M03 | 文本指令 | 发送「截个图」 | 完成并返回截图路径 |
| M04 | 打开浏览器 | 「在浏览器中搜索测试」 | Edge 打开并使用默认搜索引擎 |
| M05 | LangGraph | 多步任务中途刷新 | 状态恢复或正确显示 |
| M06 | 操作确认 | L2 删除类指令 | 弹确认；拒绝则不执行 |
| M07 | Kill Switch | 点击紧急停止 | 立即停止键鼠模拟 |
| M08 | 认证 | 未登录访问 API | 401；登录后 200 |
| M09 | 审计日志 | 执行一条指令后查询 | 完整记录 |

---

## Phase 2 — 多模态冒烟

| # | 测试项 | 通过标准 |
|---|--------|----------|
| V01 | 摄像头 WebSocket 流 | 页面实时画面，延迟 <500ms |
| V02 | 人员出现规则 | 入镜触发通知 |
| A01 | 语音「打开记事本」 | ASR 正确 + 记事本启动 |
| A02 | 语音快捷（不经 LLM） | 响应 <1s |
| R01 | 规则 CRUD | Web UI 增删改查生效 |

---

## Phase 3/4 — 高阶冒烟

| # | 测试项 | 通过标准 |
|---|--------|----------|
| G01 | 手势触发 | 指定手势执行宏 |
| G02 | 虚拟屏校准 | 九点校准后点击误差 <30px |
| T01 | TTS 反馈 | 任务完成语音播报 |
| L01 | Lite 限额 | 超额被拒绝并提示升级 |
| S01 | 局域网访问 | 白名单 IP 可访问；其他拒绝 |

---

## 手动验收示例（E06 摄像头）

```powershell
$env:PYTHONPATH = "I:\SenseHub Agent"
& "I:\SenseHub Agent\.venv\Scripts\python" -c @"
import cv2
cap = cv2.VideoCapture(0)
ok, frame = cap.read()
cap.release()
print('OK' if ok and frame is not None else 'FAIL')
"@
```

## 手动验收示例（E12 LLM）

```powershell
& "I:\SenseHub Agent\.venv\Scripts\python" scripts\smoke\test_llm.py
```

---

## 相关文档

- [环境预配置](SETUP.md)
- [产品规格](SPEC.md)
