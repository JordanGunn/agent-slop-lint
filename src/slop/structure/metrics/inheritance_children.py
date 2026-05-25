"""``inheritance.children`` — NOC (Number of Children, CK 1994).

Class-scope only. NOC counts a class's direct subclasses within the
corpus (grandchildren do not count; that's a different metric).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.structure.metrics._class_index import _class_index, _class_threshold, _slop
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure


def run_inheritance_children(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: Config,
) -> RuleResult:
    """NOC — flag classes whose direct subclass count exceeds the threshold."""
    threshold = _class_threshold(rule_config, 10)
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    groups, _, children_map, _ = _class_index(structure)
    findings: list[tuple[int, Slop]] = []
    if threshold is not None:
        for canonical, _members in groups:
            noc = structure.subclasses_count(canonical, children_map)
            if noc > threshold:
                slop = _slop(
                    "inheritance.children",
                    canonical, root, severity, noc, threshold,
                    f"NOC {noc} exceeds {threshold}",
                )
                slop.scope = "class"
                findings.append((noc, slop))
    findings.sort(key=lambda t: -t[0])
    violations = [v for _, v in findings]
    return RuleResult(
        rule="inheritance.children",
        status="fail" if violations else "pass",
        violations=violations,
        summary={"classes_checked": len(groups), "violation_count": len(violations)},
        errors=[],
    )

RULE = RuleDefinition(
    name=Tag.CHILDREN.key,
    category=Tag.CHILDREN.key,
    description='NOC — direct subclass count (CK 1994)',
    default_severity='error',
    default_enabled=True,
    threshold_label='NOC > 10',
    run=run_inheritance_children,
    scopes=('class',),
)
