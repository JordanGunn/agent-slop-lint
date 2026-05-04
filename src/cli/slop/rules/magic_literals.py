"""Magic literal density rule — wraps magic_literals_kernel.

Rules:
  information.magic_literals  — flag functions that contain more than
                                ``threshold`` distinct non-trivial numeric
                                literals in their bodies.

A numeric literal that has no symbolic name (no constant declaration) forces
the reader to guess its meaning from context.  Clusters of such literals in a
single function are a reliable signal that the function embeds domain logic
that should live in named constants or configuration.

The trivial constants 0, 1, -1, and 2 are excluded from counting; see
``_structural/magic_literals.py`` for the full exclusion list.

Config params
-------------
  threshold  int   Maximum number of distinct non-trivial numeric literals
                   allowed per function (default: 3).
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.magic_literals import magic_literals_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_magic_literal_density(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Flag functions with too many magic numeric literals."""
    threshold: int = int(rule_config.params.get("threshold", 3))
    severity = rule_config.severity

    result = magic_literals_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
    )

    violations: list[Violation] = []
    for entry in result.entries:
        if entry.distinct_count > threshold:
            violations.append(
                Violation(
                    rule="information.magic_literals",
                    file=entry.file,
                    line=entry.line,
                    symbol=entry.name,
                    message=(
                        f"'{entry.name}' contains {entry.distinct_count} distinct "
                        f"magic numeric literals (threshold: {threshold}): "
                        + ", ".join(sorted(set(entry.literals)))
                    ),
                    severity=severity,
                    value=entry.distinct_count,
                    threshold=threshold,
                    metadata={
                        "language": entry.language,
                        "literals": sorted(set(entry.literals)),
                        "distinct_count": entry.distinct_count,
                    },
                )
            )

    return RuleResult(
        rule="information.magic_literals",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_analyzed": result.functions_analyzed,
            "files_searched": result.files_searched,
            "violations": len(violations),
            "threshold": threshold,
        },
        errors=list(result.errors),
    )
