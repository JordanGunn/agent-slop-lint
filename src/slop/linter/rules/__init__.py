"""Cross-cutting rule registry.

Rules that don't fit a single view: ``structural.hotspots`` needs git
churn history, and ``structural.orphans`` needs whole-tree reference
analysis. They live with the linter rather than the structure or
lexicon view.
"""
from __future__ import annotations

from slop.linter._shim import legacy_v2_shim
from slop.linter.types import RuleDefinition

from .dead_code import run_unreferenced
from .hotspots import run_churn_weighted

CROSS_CUTTING_RULES: list[RuleDefinition] = [
    RuleDefinition(
        name="structural.hotspots",
        category="structural.hotspots",
        description="Churn × complexity per file (Tornhill 2015)",
        default_severity="error",
        default_enabled=True,
        threshold_label="14d window",
        run=legacy_v2_shim(run_churn_weighted),
    ),
    RuleDefinition(
        name="structural.orphans",
        category="structural.orphans",
        description="Unreferenced symbols (advisory)",
        default_severity="warning",
        default_enabled=False,
        threshold_label="",
        run=legacy_v2_shim(run_unreferenced),
    ),
]
