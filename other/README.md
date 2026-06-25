# other

本目录存放从远程仓库合并进来、**不属于 SenseHub Agent 主工程**的参考/实验代码与模型文件（原位于 `sensehub/` 下）。

主项目运行不依赖此目录。若需使用其中脚本，请自行安装依赖并在本目录内调试。

| 路径 | 说明 |
|------|------|
| `sensehub/perception/multimodal.py` | 多模态感知实验脚本（YOLO、手势等） |
| `sensehub/perception/*.task` | MediaPipe 模型文件 |
| `sensehub/execution/*_enhanced.py` 等 | 增强版工具/浏览器封装（未接入主 Tool Registry） |
| `sensehub/execution/tools/screenshot_interactive.py` | 交互式区域截图（Tk 全屏选区，未接入主 Tool Registry） |
| `scripts/smoke/test_game` | 五子棋 smoke 脚本（DeepSeek API 对弈实验） |
