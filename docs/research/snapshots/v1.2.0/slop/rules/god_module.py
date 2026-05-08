"""God-module rule — wraps god_module_kernel.

Rules:
  structural.god_module  — flag files with too many top-level callable
                           definitions (functions + classes)

A file that defines many unrelated top-level symbols is a god module.  It
resists focused ownership, makes test isolation expensive, and forces every
reader to skim the whole file to understand the scope.

The metric is a count, not a complexity; it captures breadth, not depth.
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.god_module import god_module_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_god_module(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Flag files whose top-level definition count exceeds the threshold."""
    threshold: int = rule_config.params.get("threshold", 20)
    severity = rule_config.severity

    result = god_module_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
    )

    violations: list[Violation] = []
    for entry in result.entries:
        if entry.definition_count > threshold:
            violations.append(
                Violation(
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
