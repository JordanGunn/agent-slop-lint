"""``complexity.density`` — Halstead D = (η₁/2) · (N₂/η₂).

Function-scope only. D is a density ratio (not additive), so class-
scope aggregation would be dimensionally incoherent — no class
variant exists.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.tags import Tag
from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.structure.metrics._halstead import _halstead_for, _slop
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure


def run_density(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: Config,
) -> RuleResult:
    """Halstead D at function scope only — D is non-additive across methods."""
    thresholds = rule_config.params.get("thresholds", {}) or {}
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    findings: list[tuple[float, Slop]] = []
    functions_analyzed = 0

    fn_threshold = thresholds.get("function")
    if fn_threshold is None:
        return RuleResult(
            rule=Tag.DENSITY.key,
            status="pass",
            violations=[],
            summary={"functions_analyzed": 0, "violations": 0},
            errors=[],
        )

    for c in structure.callables():
        functions_analyzed += 1
        metrics = _halstead_for(structure, c)
        if metrics is None:
            continue
        n1, n2, _total_n1, total_n2 = metrics
        if n2 == 0:
            continue
        density = (n1 / 2) * (total_n2 / n2)
        if density > fn_threshold:
            slop = _slop(
                Tag.DENSITY.key,
                c, root, severity, density, fn_threshold,
                f"Density {density:.1f} exceeds {fn_threshold:.0f}",
                {"n1": n1, "n2": n2, "total_n2": total_n2},
            )
            slop.scope = "function"
            findings.append((density, slop))

    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule=Tag.DENSITY.key,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_analyzed": functions_analyzed,
            "violations": len(violations),
        },
        errors=[],
    )

RULE = RuleDefinition(
    name=Tag.DENSITY.key,
    category=Tag.COMPLEXITY.key,
    description='Halstead D = (η₁/2)·(N₂/η₂) per function (Halstead 1977). Non-additive — function-scope only.',
    default_severity='error',
    default_enabled=True,
    threshold_label='D > 30',
    run=run_density,
    scopes=('function',),
)
