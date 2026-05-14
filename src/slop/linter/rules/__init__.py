"""Cross-cutting rule registry.

Rules that don't fit a single view: ``structural.hotspots`` needs git
churn history, and ``structural.orphans`` needs whole-tree reference
analysis. They live with the linter rather than the structure or
lexicon view.
"""
from __future__ import annotations

from slop.linter.types import RuleDefinition

from .hotspots import run_churn_weighted
from .orphans import run_orphans

CROSS_CUTTING_RULES: list[RuleDefinition] = [
    RuleDefinition(
        name="structural.hotspots",
        category="structural.hotspots",
        description="Churn × complexity per file (Tornhill 2015)",
        default_severity="error",
        default_enabled=True,
        threshold_label="14d window",
        run=run_churn_weighted,
    ),
    RuleDefinition(
        name="structural.orphans",
        category="structural.orphans",
        description="Unreferenced symbols (advisory)",
        default_severity="warning",
        default_enabled=False,
        threshold_label="",
        run=run_orphans,
    ),
]
