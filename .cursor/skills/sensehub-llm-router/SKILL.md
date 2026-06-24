---
name: sensehub-llm-router
description: Configure LLM routing for SenseHub—SiliconFlow Qwen, Volcengine Doubao, models.yaml roles, fallbacks. Use when editing sensehub/cognition/ or config/models.yaml.
---

# SenseHub LLM Router

## Providers (dev)

- **siliconflow**: `SILICONFLOW_API_KEY`, `SILICONFLOW_BASE_URL` — intent, coder, vision, safety
- **volcengine**: `VOLCENGINE_API_KEY`, `VOLCENGINE_BASE_URL` — planner

## Roles (`config/models.yaml`)

| Role | Purpose |
|------|---------|
| intent | Classify + entities |
| planner | Multi-step JSON plan |
| coder | Script/selectors |
| vision | Screenshot summary |
| safety | Block dangerous plans |

## Rules

- Keys only from `config/local.env` via `Settings`
- Use `LLMRouter.chat()` / `chat_json()` in `cognition/router.py`
- Planner output must be JSON with `steps[]`; strip markdown fences if present
- Implement fallback chain from `models.yaml` `fallback`
- Never log API keys

## 答辩切换

Update `models.yaml` roles + env keys (e.g. DeepSeek)—no code changes required.
