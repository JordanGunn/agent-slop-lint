"""``slop.config`` — config loading + dataclasses.

Re-exports the loader entry points and the three config dataclasses
for ergonomic ``from slop.config import load_config, SlopConfig`` use.
"""
from __future__ import annotations

from .loader import DEFAULT_RULE_CONFIGS, generate_default_config, load_config
from .models import RuleConfig, SlopConfig, WaiverConfig

__all__ = [
    "load_config",
    "generate_default_config",
    "DEFAULT_RULE_CONFIGS",
    "RuleConfig",
    "SlopConfig",
    "WaiverConfig",
]
