"""感知层初始化."""

from __future__ import annotations

from sensehub.rules import store as rule_store

__all__ = ["init_perception"]


def init_perception() -> None:
    rule_store.seed_defaults()
    rule_store.ensure_perception_seed_rules()
