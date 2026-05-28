"""``complexity.volume`` — Halstead Volume V = N · log₂(η).

Function-scope: per-callable V (Halstead 1977).
Class-scope:    sum of method V (additive, so the aggregation is
                mathematically defensible). **Slop calibration** — no
                published class-scope threshold; we pick empirically.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any

from slop.config import Config
from slop.linter.rule import Rule
from slop.linter.rules.class_index import _class_index
from slop.linter.rules.halstead import _halstead_for, _slop
from slop.linter.slop import Slop
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition, RuleResult

if TYPE_CHECKING:
    from slop.structure.view import Structure


_RULE = Tag.VOLUME.key

def run(
    structure: Structure,
    rule_config: Rule,
    slop_config: Config,
) -> RuleResult:
    """Halstead V at function scope; sum of method V at class scope."""
    thresholds = rule_config.params.get("thresholds", {}) or {}
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    findings: list[tuple[float, Slop]] = []
    functions_analyzed = 0
    classes_checked = 0

    # Cache per-callable volumes so the class-scope aggregate can reuse.
    volumes: dict[Any, float] = {}

    fn_threshold = thresholds.get("function")
    for c in structure.callables():
        functions_analyzed += 1
        metrics = _halstead_for(structure, c)
        if metrics is None:
            continue
        n1, n2, total_n1, total_n2 = metrics
        if n1 + n2 == 0:
            continue
        volume = (total_n1 + total_n2) * math.log2(n1 + n2)
        volumes[c.qualname] = volume
        if fn_threshold is not None and volume > fn_threshold:
            findings.append((volume, _slop(
                _RULE,
                c, root, severity, volume, fn_threshold,
                f"Volume {volume:.1f} exceeds {fn_threshold:.0f}",
                {"n1": n1, "n2": n2, "total_n1": total_n1, "total_n2": total_n2},
            )))

    # Re-tag function-scope findings.
    for _, slop in findings:
        slop.scope = "function"

    cls_threshold = thresholds.get("class")
    if cls_threshold:
        # Reuse the class-scope Slop builder from _class_index for symmetry
        # with the other class-scope rules.
        from slop.linter.rules.class_index import _slop as _class_slop
        groups, _, _, _ = _class_index(structure)
        for canonical, members in groups:
            classes_checked += 1
            agg = sum(volumes.get(m.qualname, 0.0) for m in members)
            if agg > cls_threshold:
                slop = _class_slop(
                    _RULE, canonical, root, severity,
                    agg, cls_threshold,
                    f"Class V sum {agg:.1f} exceeds {cls_threshold:.0f}",
                )
                slop.scope = "class"
                findings.append((agg, slop))

    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule=_RULE,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_analyzed": functions_analyzed,
            "classes_checked": classes_checked,
            "violations": len(violations),
        },
        errors=[],
    )

RULE = RuleDefinition(
    name=_RULE,
    category=Tag.COMPLEXITY.key,
    description='Halstead Volume V = N·log₂η per function (Halstead 1977); method-sum per class (slop calibration)',
    default_severity='error',
    default_enabled=True,
    threshold_label='V > 1500 / Σ > 6000',
    run=run,
    scopes=('function', 'class'),
)
