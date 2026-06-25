# 灵枢 SenseHub 团队分工说明（TEAM）

> **文档版本**：v1.0（内部参考）

团队按系统分层划分职责，适用于研发协作与交付分工记录。

## 角色一览

| 角色 | 负责模块 | 主要工作 |
|------|----------|----------|
| **组长** | 架构 · 集成 · 安全 | 技术方案与接口定义、代码合并、安全与档位、测试验收、进度协调 |
| **组员 A** | 感知层 | 摄像头采集、YOLO 视觉检测、Whisper/FunASR 语音识别、手势与虚拟屏 |
| **组员 B** | 认知与编排 | LLM 多模型路由、意图解析、任务规划、LangGraph 状态机 |
| **组员 C** | 执行层 | PyAutoGUI 桌面操作、Playwright 网页自动化、文件管理与截图 |
| **组员 D** | Web 与交互 | FastAPI 接口、WebSocket 实时通信、React 控制台 UI |

## 协作关系

```
用户 → 组员D（Web）→ 组员B（规划）→ 组员C（执行）
              ↑              ↑
        组员A（视/听）    组员C（反馈截图）
              ↓
        组员D（状态展示）

组长：定义接口、合并主线、安全把关、阶段验收
```

## 代码目录归属

| 成员 | 目录 |
|------|------|
| 组长 | `sensehub/security/`、`sensehub/licensing/`、`docs/`、`config/` |
| 组员 A | `sensehub/perception/` |
| 组员 B | `sensehub/cognition/`、`sensehub/orchestration/` |
| 组员 C | `sensehub/execution/`、`sensehub/rules/`（动作侧） |
| 组员 D | `sensehub/api/`、`web/` |

## 阶段分工（摘要）

| 阶段 | 组长 | A | B | C | D |
|------|------|---|---|---|---|
| Phase 0 | 脚手架、架构文档 | 感知模块骨架 | 编排模块骨架 | 执行工具骨架 | API/UI 初始化 |
| Phase 1 | 认证、联调、验收 | — | 文本规划链路 | 桌面/网页执行 | 指令页 + 任务状态 |
| Phase 2 | 规则框架 | 摄像头 + YOLO + 语音 | 多模型路由 | 文件操作 | 预览页 + 规则页 |
| Phase 3+ | 档位与审计 | 流式 ASR、手势 | 确认门控 | 复杂流程 | 安全中心、档位 UI |

## 协作约定

- 接口变更由组长评审，更新 `docs/ARCHITECTURE.md` 后同步全员
- 功能分支：`feat/<角色>-<简述>`，组长合并 `main`
- 每周一次集成联调，Phase 结束跑冒烟测试
