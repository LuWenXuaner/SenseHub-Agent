---
name: sensehub-agent
description: Build SenseHub Agent core logic—LangGraph orchestration, execution tools, task state. Use when editing sensehub/orchestration/, sensehub/execution/, task runner, or tool registry.
---

# SenseHub Agent Core

## Rules

- Register tools in `sensehub/execution/tools/registry.py` with risk level L0–L3
- LangGraph/runner state must persist via `sensehub/db/tasks.py`
- Load paths from `config/paths.yaml` via `get_settings()`—never hardcode disk paths
- Check `sensehub/licensing/tier.py` before creating tasks
- Write audit via `sensehub/security/audit.log_audit` after execution
- Kill Switch: `sensehub/execution/kill_switch.py` checked before PyAutoGUI/Playwright
- Errors: user-readable message + `trace_id` on tasks

## Tool chain

`plan (LLM) → safety review → wait_confirm (L2) → execute → report`

## Adding a tool

1. Implement `run(params) -> dict` in `sensehub/execution/tools/`
2. Register in `REGISTRY` with default risk level
3. Document in planner system prompt (`cognition/planner.py`)
