---
id: document-delivery
name: 文档与海报交付规程
description: Word/Excel/PPT/海报生成并保存
tier_min: lite
triggers:
  - word
  - excel
  - ppt
  - docx
  - xlsx
  - pptx
  - 文档
  - 海报
  - 幻灯片
  - 表格
---

## 选型

| 场景 | 工具 |
|------|------|
| 标题+正文、简单表格、几页幻灯片 | `generate_document` |
| 海报、复杂排版、图表、多样式 | `run_document_script` |

## run_document_script 约定

- 参数：`code`（完整 Python）、`output_path`（相对路径默认落用户保存目录）
- 沙箱注入变量：`OUTPUT_PATH`（Path，**必须写入**）、`SAVE_DIR`（Path）
- 库：`python-docx`、`openpyxl`、`python-pptx`、`Pillow` 等
- 禁止：subprocess、网络、删系统文件

## 示例（海报 PNG）

```python
from PIL import Image, ImageDraw, ImageFont

img = Image.new("RGB", (900, 1200), "#1a1a2e")
draw = ImageDraw.Draw(img)
draw.text((80, 200), "标题", fill="white")
img.save(OUTPUT_PATH)
```

## 禁止

- 用 GUI 模拟在 Office 里排版（慢且不可靠）
- 脚本写入沙箱外路径
