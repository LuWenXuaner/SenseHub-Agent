---
name: sensehub-ui
description: Build and modify the SenseHub Agent web console (web/). Enforces dual light/dark themes, shadcn/ui + Tailwind, tier-aware UI (Lite/Pro/Max), multimodal layout slots for camera/voice/virtual-screen, and dashboard patterns. Use when creating pages, components, styling, routing, or UX for the 灵枢 Agent React frontend.
---

# SenseHub UI Skill

## Must Read First

- Design master plan: [`docs/UI_DESIGN.md`](../../../docs/UI_DESIGN.md)
- Tier features: [`docs/TIERS.md`](../../../docs/TIERS.md)
- External UX reference (do not copy wholesale): [`skills-example/`](../../../skills-example/)

## Product Context

灵枢 Agent is a **multimodal control console** (text, voice, camera, desktop automation)—not a marketing landing page. Design for **Phase 1 through Phase 4** in one coherent shell; never rebuild layout from scratch per phase.

## Non-Negotiables

1. **Dual theme (light + dark)** — CSS variables only; Tailwind `darkMode: 'class'`; user picks light/dark/system in Settings + TopBar toggle.
2. **Holistic layout** — Use shared `AppShell` (Sidebar + TopBar + CommandDock). Phase 2+ slots exist from day one (placeholder cards OK).
3. **Tier-aware UI** — Same app for Lite/Pro/Max. Locked features stay **visible** with `TierGate` (lock icon + upgrade CTA), not hidden routes.
4. **Multimodal-ready** — Reserve Dashboard grid for camera 16:9 + voice panel; CommandDock supports text now, voice button stub until Phase 2.
5. **Config-driven** — No hardcoded API keys; tier/usage from backend `/api/license` or equivalent.

## Stack

- React + Vite + TypeScript (strict)
- Tailwind CSS + shadcn/ui (Radix primitives)
- TanStack Query for REST; native WebSocket for tasks/camera streams
- Icons: Lucide (no emoji as icons)

Reference implementation patterns: `skills-example/ui-ux-pro-max-skill-main/.claude/skills/ui-styling/`

## Design Tokens

Use semantic tokens from `docs/UI_DESIGN.md` §4. Example:

```css
/* web/src/styles/theme.css */
:root { --primary: #6366F1; --background: #FAFAFA; /* ... */ }
.dark { --primary: #818CF8; --background: #0F1117; /* ... */ }
```

Never use raw `#fff`/`#000` in components. Map shadcn theme to these variables.

## Layout Components (create once, reuse everywhere)

| Component | Role |
|-----------|------|
| `AppShell` | Sidebar groups + TopBar + outlet |
| `TopBar` | Logo, AgentStatusChip, tier badge, theme toggle, KillSwitch |
| `Sidebar` | Console / Perception / Automation / System nav |
| `CommandDock` | Fixed bottom: text input, send, voice btn (tier-gated) |
| `TierGate` | Wrap feature; show lock + UpgradePrompt if tier insufficient |
| `UsageMeter` | Progress for daily limits (Lite text commands) |

## Routing

Implement full route table from `UI_DESIGN.md` §2. Unready pages: render `ComingSoonPage` with tier hint, not 404.

## Tier UI Rules

| Case | UI |
|------|-----|
| Feature allowed | Normal |
| Feature locked (lower tier) | Visible nav + TierGate overlay + link `/billing` |
| Quota exceeded | Toast + red UsageMeter + disable send |

Tier badge in TopBar: Lite (muted), Pro (primary), Max (accent border).

## Multimodal Components (stubs OK in Phase 1)

- `CameraPreviewCard` — 16:9, overlay canvas for YOLO boxes (Phase 2 WebSocket)
- `VoicePanel` — waveform + transcript (Phase 2)
- `VirtualScreenCalibrator` — Max only, TierGate locked until Phase 4
- Perception toggles default **OFF**; show privacy copy when enabling

## UX Priority (from ui-ux-pro-max)

1. Accessibility: contrast 4.5:1, focus rings, aria-labels
2. Interaction: 44px touch targets, loading states on all async actions
3. Performance: lazy-load heavy pages; reserve space to avoid CLS
4. Motion: 150–300ms transitions; respect `prefers-reduced-motion`

## Anti-Patterns

- Purple-gradient-on-white generic AI landing aesthetics
- Hiding Pro/Max nav items entirely on Lite
- Separate codebase per tier
- Hardcoded colors bypassing CSS variables
- Camera/voice UI added later by breaking Dashboard grid
- Async buttons without loading/disabled state

## File Organization

```
web/src/components/layout/   AppShell, Sidebar, TopBar, CommandDock
web/src/components/tier/     TierGate, UpgradePrompt, UsageMeter
web/src/components/tasks/    TaskTimeline, StepCard
web/src/components/perception/  Phase 2+
web/src/pages/               One folder per route group
web/src/hooks/useTheme.ts
web/src/hooks/useTier.ts
web/src/styles/theme.css
```

## When Editing

- New page → add to Sidebar + route table in UI_DESIGN.md if new section
- New paid feature → wrap with TierGate + document in TIERS.md
- New perception UI → fit Dashboard grid or `/perception/*`, not ad-hoc modal only
