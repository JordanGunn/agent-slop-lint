"""Dead-code rules — wraps the vendored prune_kernel.

Rules:
  structural.orphans  — report unreferenced symbols (advisory by default)
"""

from __future__ import annotations

from pathlib import Path

from slop._compose.prune import prune_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation

_CONFIDENCE_ORDER = {"high": 3, "medium": 2, "low": 1}


def run_unreferenced(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Report unreferenced symbols above a confidence threshold."""
    min_confidence = rule_config.params.get("min_confidence", "high")
    min_confidence_level = _CONFIDENCE_ORDER.get(min_confidence, 3)
    severity = rule_config.severity

    result = prune_kernel(
        root=root,
        excludes=slop_config.exclude or None,
    )

    violations: list[Violation] = []
    for candidate in result.candidates:
        candidate_level = _CONFIDENCE_ORDER.get(candidate.confidence, 0)
        if candidate_level >= min_confidence_level:
            violations.append(
                Violation(
                    rule="structural.orphans",
                    file=candidate.file,
                    line=candidate.line if candidate.line > 0 else None,
                    symbol=candidate.symbol,
                    message=(
                        f"{candidate.external_refs} references "
                        f"({candidate.confidence} confidence)"
                    ),
                    severity=severity,
                    value=candidate.external_refs,
                    threshold=0,
                    metadata={
                        "symbol_type": candidate.symbol_type,
                        "confidence": candidate.confidence,
                        "caveats": candidate.caveats,
                    },
                )
            )

    return RuleResult(
        rule="structural.orphans",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "symbols_analyzed": result.symbols_analyzed,
            "candidates_found": len(violations),
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
