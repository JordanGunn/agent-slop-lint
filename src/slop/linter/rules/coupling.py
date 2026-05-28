"""``coupling`` — CBO (Coupling Between Objects, Chidamber & Kemerer 1994).

Class-scope only. CBO measures the count of distinct outbound class
references from a given class. There is no principled aggregation to
package scope (that would be a different metric — fan-out, not CBO).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.rules.class_index import _class_index, _class_threshold, _slop
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure


_RULE = Tag.COUPLING.key

def run(
    structure: Structure,
    rule_config: Rule,
    slop_config: Config,
) -> RuleResult:
    """CBO — flag classes whose distinct outbound class-references exceed the threshold."""
    threshold = _class_threshold(rule_config, 8)
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    groups, _, _, known = _class_index(structure)
    findings: list[tuple[int, Slop]] = []
    if threshold is not None:
        for canonical, members in groups:
            # Max CBO across members (Ruby re-openings; singleton otherwise).
            cbo = max((structure.coupling(m, known) for m in members), default=0)
            if cbo > threshold:
                slop = _slop(
                    "coupling",
                    canonical, root, severity, cbo, threshold,
                    f"CBO {cbo} exceeds {threshold}",
                )
                slop.scope = "class"
                findings.append((cbo, slop))
    findings.sort(key=lambda t: -t[0])
    violations = [v for _, v in findings]
    return RuleResult(
        rule="coupling",
        status="fail" if violations else "pass",
        violations=violations,
        summary={"classes_checked": len(groups), "violation_count": len(violations)},
        errors=[],
    )

RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description='CBO — count of classes a given class is coupled to (CK 1994)',
    default_severity='error',
    default_enabled=True,
    threshold_label='CBO > 8',
    run=run,
    scopes=('class',),
)
