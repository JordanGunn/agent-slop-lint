"""God-module rule — flag files with too many top-level definitions.

A file that defines many unrelated top-level symbols is a god module. It
resists focused ownership, makes test isolation expensive, and forces
every reader to skim the whole file to understand its scope.

The metric is a count, not a complexity; it captures breadth, not depth.
Methods inside a class don't count toward god-module (they're a god-class
signal — see ``class.complexity`` / WMC). Lambdas don't count
(they're inline values, not definitions).
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.tags import Tag
from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.tree.records import CallableKind, ScopeKind
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure


_TOP_LEVEL_SCOPE_KINDS: frozenset[ScopeKind] = frozenset({
    ScopeKind.FILE, ScopeKind.MODULE, ScopeKind.PACKAGE,
})

_CLASS_LIKE_SCOPE_KINDS: frozenset[ScopeKind] = frozenset({
    ScopeKind.CLASS, ScopeKind.INTERFACE, ScopeKind.STRUCT,
    ScopeKind.TRAIT, ScopeKind.IMPL,
})


def run_god_module(
    structure: Structure,
    rule_config: Rule,
    slop_config: Config,
) -> RuleResult:
    """Flag files whose top-level definition count exceeds threshold.

    "Top-level" means the definition's parent is a FILE / MODULE /
    PACKAGE scope (not a class-like scope). Methods inside classes
    naturally fall out of the count. Lambdas are skipped (inline
    values, not definitions).
    """
    thresholds = rule_config.params.get("thresholds", {}) or {}
    if "module" not in thresholds:
        return RuleResult(
            rule=Tag.GOD_MODULE.key, status="pass", violations=[],
            summary={"files_checked": 0, "violation_count": 0},
        )
    threshold: int = int(thresholds.get("module", 20))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    module_scope_qualnames: set[str] = {
        s.qualname for s in structure.scopes()
        if s.kind in _TOP_LEVEL_SCOPE_KINDS
    }

    counts: dict[Path, int] = defaultdict(int)
    files_checked: set[Path] = set()

    for c in structure.callables():
        files_checked.add(c.path)
        if c.kind == CallableKind.LAMBDA:
            continue
        if c.parent is None or c.parent in module_scope_qualnames:
            counts[c.path] += 1

    for s in structure.scopes():
        files_checked.add(s.path)
        if s.kind not in _CLASS_LIKE_SCOPE_KINDS:
            continue
        if s.parent is None or s.parent in module_scope_qualnames:
            counts[s.path] += 1

    findings: list[tuple[int, Slop]] = []
    for path, count in counts.items():
        if count > threshold:
            try:
                rel = str(path.relative_to(root))
            except ValueError:
                rel = str(path)
            findings.append((count, Slop(
                rule=Tag.GOD_MODULE.key,
                file=rel,
                line=None,
                symbol=None,
                message=f"{count} top-level definitions exceeds {threshold}",
                severity=severity,
                value=count,
                threshold=threshold,
                metadata={},
                scope="module",
            )))

    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule=Tag.GOD_MODULE.key,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_checked": len(files_checked),
            "violation_count": len(violations),
        },
    )

RULE = RuleDefinition(
    name=Tag.GOD_MODULE.key,
    category=Tag.GOD_MODULE.key,
    description='Files with too many top-level callable definitions',
    default_severity='warning',
    default_enabled=True,
    threshold_label='> 20',
    run=run_god_module,
    scopes=('module',),
)
