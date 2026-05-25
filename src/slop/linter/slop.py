"""``Slop`` — the v2.0 finding type.

Replaces ``models.Slop`` once the deletion sweep completes. Field
names deliberately mirror ``Slop`` so the two types coexist in
``RuleResult.violations`` via attribute-name duck typing during the
migration window. The new ``suggestion`` field is the carrier for
agent-facing corrective hints (see ``docs/planning/linter.md`` — the
telemetry layer).

Output-side type — semantically distinct from the parse-entity records
in ``corpus/records.py``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Slop:
    """A finding emitted by a rule.

    The ``scope`` field declares the emission unit (``function``, ``class``,
    ``module``, ``parameter``, ``package``) — first-class since the
    scope-as-first-class refactor. ``None`` is reserved for cross-cutting
    rules whose emission unit doesn't map to a single scope (cycles, hotspot
    files, orphan symbols).
    """

    rule: str
    file: str
    line: int | None = None
    symbol: str | None = None
    message: str = ""
    severity: str = "error"
    value: float | int | None = None
    threshold: float | int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    suggestion: str | None = None
    scope: str | None = None
