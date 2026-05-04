"""Any-type density rule — wraps any_type_density_kernel.

Rules:
  structural.types.escape_hatches  — flag files where a significant fraction of
                                 type annotations use the language's escape-
                                 hatch type (Python Any, Go any/interface{},
                                 TypeScript any, Java Object, C# dynamic).

Config params
-------------
  threshold      float   Maximum tolerated density (0.0–1.0).
                         Default: 0.30 (flag if > 30% of annotations are Any).
  min_annotations int    Minimum annotation count before density is computed.
                         Avoids noise from files with only 1–2 annotations.
                         Default: 5.
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.any_type_density import any_type_density_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation

DEFAULT_THRESHOLD = 0.30
DEFAULT_MIN_ANNOTATIONS = 5
PRECISION = 4


def run_any_type_density(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Flag files where too many type annotations use escape-hatch types."""
    threshold: float = float(rule_config.params.get("threshold", DEFAULT_THRESHOLD))
    min_annotations: int = int(rule_config.params.get("min_annotations", DEFAULT_MIN_ANNOTATIONS))
    severity = rule_config.severity

    result = any_type_density_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
    )

    violations: list[Violation] = []
    for entry in result.entries:
        if entry.total_count < min_annotations:
            continue
        if entry.density > threshold:
            pct = entry.density * 100
            violations.append(
                Violation(
                    rule="structural.types.escape_hatches",
                    file=entry.file,
                    line=None,
                    symbol=None,
                    message=(
                        f"{pct:.1f}% of type annotations in '{entry.file}' "
                        f"use escape-hatch types "
                        f"({entry.escape_count}/{entry.total_count})"
                    ),
                    severity=severity,
                    value=round(entry.density, PRECISION),
                    threshold=threshold,
                    metadata={
                        "language": entry.language,
                        "escape_count": entry.escape_count,
                        "total_count": entry.total_count,
                        "density": entry.density,
                    },
                )
            )

    return RuleResult(
        rule="structural.types.escape_hatches",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_scanned": result.files_searched,
            "violations": len(violations),
            "threshold": threshold,
        },
        errors=list(result.errors),
    )
