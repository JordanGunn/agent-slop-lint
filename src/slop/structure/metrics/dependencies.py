"""Dependencies rules — Acyclic Dependencies Principle enforcement.

Rules:
  ``deps``  — fail if any dependency cycles exist

The Acyclic Dependencies Principle (Lakos 1996; Martin 2002 ch. 20)
holds that import cycles prevent independent reasoning about, testing
of, or extraction of any module in the cycle — every change touches
the whole loop. ``Structure.dependency_cycles`` runs Tarjan's (1972)
SCC algorithm over the resolved file→file import graph; this rule
threshold-checks the result.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure


def run_cycles(
    structure: Structure, rule_config: RuleConfig, slop_config: Config,
) -> RuleResult:
    """Flag every import cycle in the corpus."""
    del slop_config
    fail_on_cycles = rule_config.params.get("fail_on_cycles", True)
    severity = rule_config.severity

    cycles = structure.dependency_cycles()
    files_analyzed = len(structure.dependency_graph().efferent)

    violations: list[Slop] = []
    if fail_on_cycles:
        for cycle in cycles:
            cycle_str = " → ".join(cycle)
            violations.append(Slop(
                rule="deps",
                file=cycle[0] if cycle else "",
                line=None,
                symbol=None,
                message=f"cycle: {cycle_str}",
                severity=severity,
                value=len(cycle),
                threshold=0,
                metadata={"cycle": cycle},
            ))

    return RuleResult(
        rule="deps",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_analyzed": files_analyzed,
            "cycles_found": len(cycles),
            "violation_count": len(violations),
        },
    )

RULE = RuleDefinition(
    name=Tag.DEPS.key,
    category=Tag.DEPS.key,
    description='Dependency cycle detection',
    default_severity='error',
    default_enabled=True,
    threshold_label='cycles',
    run=run_cycles,
    scopes=(),
)
