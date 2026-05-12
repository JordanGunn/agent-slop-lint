"""God-module rule — flag files with too many top-level definitions.

A file that defines many unrelated top-level symbols is a god module. It
resists focused ownership, makes test isolation expensive, and forces every
reader to skim the whole file to understand its scope.

The metric is a count, not a complexity; it captures breadth, not depth.
Methods inside a class don't count toward god-module (they're a god-class
signal — see ``structural.class.complexity`` / WMC). Lambdas don't count
(they're inline values, not definitions).
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from slop._structural.god_module import god_module_kernel
from slop.config.models import RuleConfig, SlopConfig
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.structure.view import Structure
from slop.tree.records import CallableKind, ScopeKind


_TOP_LEVEL_SCOPE_KINDS: frozenset[ScopeKind] = frozenset({
    ScopeKind.FILE, ScopeKind.MODULE, ScopeKind.PACKAGE,
})

_CLASS_LIKE_SCOPE_KINDS: frozenset[ScopeKind] = frozenset({
    ScopeKind.CLASS, ScopeKind.INTERFACE, ScopeKind.STRUCT,
    ScopeKind.TRAIT, ScopeKind.IMPL,
})


def run_god_module(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Legacy shim — calls the vendored god_module_kernel.

    Retained for any caller that still wants the legacy entry; the v2
    registry wires ``run_god_module_v2`` directly.
    """
    threshold: int = rule_config.params.get("threshold", 20)
    severity = rule_config.severity

    result = god_module_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
    )

    violations: list[Slop] = []
    for entry in result.entries:
        if entry.definition_count > threshold:
            violations.append(
                Slop(
                    rule="structural.god_module",
                    file=entry.file,
                    line=None,
                    symbol=None,
                    message=(
                        f"{entry.definition_count} top-level definitions "
                        f"exceeds {threshold} (LOC: {entry.loc})"
                    ),
                    severity=severity,
                    value=entry.definition_count,
                    threshold=threshold,
                    metadata={
                        "language": entry.language,
                        "loc": entry.loc,
                    },
                )
            )

    return RuleResult(
        rule="structural.god_module",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_checked": result.files_searched,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )


def run_god_module_v2(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    """v2 god_module — aggregate per-file count of top-level definitions.

    No view-method needed: the rule iterates ``structure.callables()``
    and ``structure.scopes()`` directly. "Top-level" means the
    definition's parent is a FILE/MODULE/PACKAGE scope (not a
    class-like scope). This naturally excludes methods inside a
    class from the count, since their parent is a CLASS-kind scope.
    """
    threshold: int = rule_config.params.get("threshold", 20)
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    # qualnames of module-level scopes — anything whose parent is one
    # of these counts as a top-level definition.
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
                rule="structural.god_module",
                file=rel,
                line=None,
                symbol=None,
                message=f"{count} top-level definitions exceeds {threshold}",
                severity=severity,
                value=count,
                threshold=threshold,
                metadata={},
            )))

    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule="structural.god_module",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_checked": len(files_checked),
            "violation_count": len(violations),
        },
        errors=[],
    )
