"""Waiver dataclass.

``Waiver`` is a scoped exception for known, bounded lint findings: it
suppresses findings for a specific (rule, path) tuple. Used sparingly
to keep exceptional findings visible without weakening global
thresholds. ``allow_up_to`` is a local relaxation; ``expires`` is an
optional ISO date after which the waiver is treated as stale and
surfaced as advisory.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Waiver:
    """Scoped exception for known, bounded lint findings."""

    id: str
    path: str
    rule: str
    reason: str
    allow_up_to: float | int | None = None
    expires: str | None = None
