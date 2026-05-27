"""``inheritance.depth`` — DIT (Depth of Inheritance Tree, CK 1994).

Class-scope only. DIT is the number of edges from a class to the root
of its inheritance tree (within the corpus); external/library bases
don't add to the count.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.rules._class_index import _class_index, _class_threshold, _slop
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure


def run_inheritance_depth(
    structure: Structure,
    rule_config: Rule,
    slop_config: Config,
) -> RuleResult:
    """DIT — flag classes whose inheritance chain depth exceeds the threshold."""
    threshold = _class_threshold(rule_config, 4)
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    groups, parent_map, _, known = _class_index(structure)
    findings: list[tuple[int, Slop]] = []
    if threshold is not None:
        for canonical, _members in groups:
            dit = structure.inheritance_depth(canonical, parent_map, known)
            if dit > threshold:
                slop = _slop(
                    "inheritance.depth",
                    canonical, root, severity, dit, threshold,
                    f"DIT {dit} exceeds {threshold}",
                )
                slop.scope = "class"
                findings.append((dit, slop))
    findings.sort(key=lambda t: -t[0])
    violations = [v for _, v in findings]
    return RuleResult(
        rule="inheritance.depth",
        status="fail" if violations else "pass",
        violations=violations,
        summary={"classes_checked": len(groups), "violation_count": len(violations)},
        errors=[],
    )

RULE = RuleDefinition(
    name=Tag.DEPTH.key,
    category=Tag.DEPTH.key,
    description='DIT — depth of inheritance tree (CK 1994)',
    default_severity='error',
    default_enabled=True,
    threshold_label='DIT > 4',
    run=run_inheritance_depth,
    scopes=('class',),
)
