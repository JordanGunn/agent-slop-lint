"""Lexical stutter rule.

Detects identifiers that repeat tokens from their enclosing scope (function,
class, or module). High stuttering indicates redundant naming that relies on
redundant context rather than descriptive naming.
"""

from __future__ import annotations

from pathlib import Path

from slop._lexical.stutter import stutter_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_stutter(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Flag identifiers that repeat tokens from their enclosing scope."""
    min_overlap: int = rule_config.params.get("min_overlap_tokens", 2)
    severity = rule_config.severity

    result = stutter_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
    )

    violations: list[Violation] = []
    for fn in result.functions:
        for v in fn.violations:
            if len(v.overlap) < min_overlap:
                continue

            violations.append(
                Violation(
                    rule="lexical.stutter",
                    file=fn.file,
                    line=v.line,
                    symbol=v.identifier,
                    message=(
                        f"identifier '{v.identifier}' repeats tokens {v.overlap} "
                        f"from enclosing {v.scope_type} '{v.scope_name}'"
                    ),
                    severity=severity,
                    value=len(v.overlap),
                    threshold=min_overlap,
                    metadata={
                        "scope_name": v.scope_name,
                        "scope_type": v.scope_type,
                        "overlap": v.overlap,
                        "identifier_tokens": v.tokens,
                    },
                )
            )

    return RuleResult(
        rule="lexical.stutter",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": len(result.functions),
            "violation_count": len(violations),
        },
        errors=result.errors,
    )
