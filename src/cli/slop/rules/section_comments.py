"""Section-comment density rule — wraps section_comment_kernel.

Rules:
  information.section_comments  — flag functions that use multiple divider-style
                                  comments as section markers inside the body.

A function with more than `threshold` section dividers (default: 2) is doing
too many conceptually distinct things.  Each divider is a signal for "extract
a helper function here".

Config params
-------------
  threshold  int   Maximum number of section dividers allowed per function.
                   Default: 2.
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.section_comments import section_comment_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_section_comment_density(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Flag functions with too many section-divider comments."""
    threshold: int = int(rule_config.params.get("threshold", 2))
    severity = rule_config.severity

    result = section_comment_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
    )

    violations: list[Violation] = []
    for entry in result.entries:
        if entry.divider_count > threshold:
            violations.append(
                Violation(
                    rule="information.section_comments",
                    file=entry.file,
                    line=entry.line,
                    symbol=entry.name,
                    message=(
                        f"'{entry.name}' contains {entry.divider_count} section "
                        f"dividers (threshold: {threshold}): "
                        f"lines {', '.join(str(line) for line in entry.divider_lines)}"
                    ),
                    severity=severity,
                    value=entry.divider_count,
                    threshold=threshold,
                    metadata={
                        "divider_lines": entry.divider_lines,
                        "language": entry.language,
                    },
                )
            )

    return RuleResult(
        rule="information.section_comments",
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
