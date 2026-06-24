"""运行时 Skills 加载."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent
_BUNDLED = Path(__file__).resolve().parent / "bundled"
_WORKSPACE = _ROOT.parent / "workspace" / "skills"


@dataclass(frozen=True)
class SkillEntry:
    id: str
    name: str
    description: str
    body: str
    triggers: tuple[str, ...]
    tier_min: str


def _parse_skill(path: Path) -> SkillEntry | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    triggers = meta.get("triggers") or []
    if isinstance(triggers, str):
        triggers = [triggers]
    return SkillEntry(
        id=str(meta.get("id") or path.parent.name),
        name=str(meta.get("name") or path.parent.name),
        description=str(meta.get("description") or ""),
        body=body,
        triggers=tuple(str(t) for t in triggers),
        tier_min=str(meta.get("tier_min") or "lite"),
    )


def load_all_skills() -> list[SkillEntry]:
    found: dict[str, SkillEntry] = {}
    for root in (_BUNDLED, _WORKSPACE):
        if not root.is_dir():
            continue
        for skill_md in root.glob("*/SKILL.md"):
            entry = _parse_skill(skill_md)
            if entry:
                found[entry.id] = entry
    return list(found.values())


def match_skills(
    user_text: str,
    intent_raw: dict | None,
    *,
    enabled: set[str] | None = None,
) -> list[SkillEntry]:
    blob = user_text.lower()
    if intent_raw:
        blob += " " + str(intent_raw.get("goal", "")).lower()
        blob += " " + str(intent_raw.get("user_wants", "")).lower()
        blob += " " + str(intent_raw.get("intent_type", "")).lower()

    from sensehub.licensing.tier import get_tier

    tier_order = {"lite": 0, "pro": 1, "max": 2}
    user_tier = tier_order.get(get_tier(), 0)

    matched: list[SkillEntry] = []
    for skill in load_all_skills():
        if enabled and skill.id not in enabled:
            continue
        if tier_order.get(skill.tier_min, 0) > user_tier:
            continue
        if not skill.triggers:
            continue
        for trig in skill.triggers:
            t = trig.lower().strip()
            if t == "desktop" and ("desktop_action" in blob or "desktop" in blob):
                matched.append(skill)
                break
            if t == "browser" and "browser" in blob:
                matched.append(skill)
                break
            if t in blob or re.search(re.escape(t), blob, re.I):
                matched.append(skill)
                break
    return matched


def format_skills_prompt(skills: list[SkillEntry]) -> str:
    if not skills:
        return ""
    blocks = []
    for s in skills:
        blocks.append(f"### Skill: {s.name}\n{s.description}\n\n{s.body}")
    return "【运行时规程 Skills】\n" + "\n\n".join(blocks)
