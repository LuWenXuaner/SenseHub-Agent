---
name: sensehub-security
description: SenseHub authentication, audit, risk levels, Kill Switch, policies. Use when editing sensehub/security/, auth routes, or policies.yaml.
---

# SenseHub Security

## Auth

- JWT via `python-jose`; password from `ADMIN_PASSWORD` in local.env
- FastAPI dependency `get_current_user` on protected routes
- Web stores token in localStorage `sensehub_token`

## Risk levels

| Level | Behavior |
|-------|----------|
| L0 | Read-only |
| L1 | Normal automation (default tools) |
| L2 | Requires Web UI confirm (`wait_confirm`) |
| L3 | Blocked by safety reviewer |

## Audit fields

`timestamp`, `user_label`, `input_text`, `action`, `risk_level`, `result`, `trace_id`

## Kill Switch

`POST /api/kill-switch` → sets global flag; execution tools must check `is_killed()`

## Network (Phase 3)

Default bind `127.0.0.1`; LAN requires `policies.yaml` + IP whitelist

## File ops

Whitelist: `SenseHubData/workspace` only (see policies.yaml)
