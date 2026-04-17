"""Rule registry for slop.

Naming scheme: every rule name reads naturally after "slop." —
  slop.complexity, slop.hotspots, slop.packages, slop.deps, slop.orphans, slop.class

Single-metric categories drop the suffix. Multi-metric categories use
category.aspect (e.g. complexity.cyclomatic, class.coupling).
"""

from __future__ import annotations

from slop.models import RuleDefinition
from slop.rules.architecture import run_distance
from slop.rules.class_metrics import run_coupling, run_inheritance_children, run_inheritance_depth
from slop.rules.complexity import run_cognitive, run_cyclomatic, run_weighted
from slop.rules.dead_code import run_unreferenced
from slop.rules.dependencies import run_cycles
from slop.rules.hotspots import run_churn_weighted

RULE_REGISTRY: list[RuleDefinition] = [
    # --- complexity (function + class level) ---
    RuleDefinition(
        name="complexity.cyclomatic",
        category="complexity",
        description="Per-function Cyclomatic Complexity (McCabe 1976)",
        default_severity="error",
        default_enabled=True,
        threshold_label="CCX > 10",
        run=run_cyclomatic,
    ),
    RuleDefinition(
        name="complexity.cognitive",
        category="complexity",
        description="Per-function Cognitive Complexity (Campbell 2018)",
        default_severity="error",
        default_enabled=True,
        threshold_label="CogC > 15",
        run=run_cognitive,
    ),
    RuleDefinition(
        name="complexity.weighted",
        category="complexity",
        description="Per-class sum of method CCX (Chidamber & Kemerer 1994)",
        default_severity="error",
        default_enabled=True,
        threshold_label="WMC > 50",
        run=run_weighted,
    ),

    # --- hotspots ---
    RuleDefinition(
        name="hotspots",
        category="hotspots",
        description="Churn \u00d7 complexity per file (Tornhill 2015)",
        default_severity="error",
        default_enabled=True,
        threshold_label="14d window",
        run=run_churn_weighted,
    ),

    # --- packages ---
    RuleDefinition(
        name="packages",
        category="packages",
        description="Package design distance (Martin 1994)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="D' > 0.7",
        run=run_distance,
    ),

    # --- deps ---
    RuleDefinition(
        name="deps",
        category="deps",
        description="Dependency cycle detection",
        default_severity="error",
        default_enabled=True,
        threshold_label="cycles",
        run=run_cycles,
    ),

    # --- orphans ---
    RuleDefinition(
        name="orphans",
        category="orphans",
        description="Unreferenced symbols (advisory)",
        default_severity="warning",
        default_enabled=False,
        threshold_label="",
        run=run_unreferenced,
    ),

    # --- class ---
    RuleDefinition(
        name="class.coupling",
        category="class",
        description="Class coupling count (Chidamber & Kemerer 1994)",
        default_severity="error",
        default_enabled=True,
        threshold_label="CBO > 8",
        run=run_coupling,
    ),
    RuleDefinition(
        name="class.inheritance.depth",
        category="class",
        description="Inheritance tree depth (Chidamber & Kemerer 1994)",
        default_severity="error",
        default_enabled=True,
        threshold_label="DIT > 4",
        run=run_inheritance_depth,
    ),
    RuleDefinition(
        name="class.inheritance.children",
        category="class",
        description="Direct subclass count (Chidamber & Kemerer 1994)",
        default_severity="error",
        default_enabled=True,
        threshold_label="NOC > 10",
        run=run_inheritance_children,
    ),
]

RULES_BY_NAME: dict[str, RuleDefinition] = {r.name: r for r in RULE_REGISTRY}

RULES_BY_CATEGORY: dict[str, list[RuleDefinition]] = {}
for _rule in RULE_REGISTRY:
    RULES_BY_CATEGORY.setdefault(_rule.category, []).append(_rule)

CATEGORIES: list[str] = sorted(RULES_BY_CATEGORY.keys())
