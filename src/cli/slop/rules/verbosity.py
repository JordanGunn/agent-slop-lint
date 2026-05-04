"""Lexical verbosity rule.

Rules:
  lexical.verbosity  — flag functions whose identifiers average
                        more than `max_mean_tokens` word-tokens

A high mean (e.g. > 3.0) means the function body is dominated by overly
wordy identifiers. Agents often produce excessively descriptive names that
repeat context already available in the scope.

The threshold `max_mean_tokens` defaults to 3.0.
"""

from __future__ import annotations

from pathlib import Path

from slop._lexical.identifier_tokens import identifier_token_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_verbosity(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Flag functions where mean identifier tokens-per-name is above threshold."""
    max_mean: float = rule_config.params.get("max_mean_tokens", 3.0)
    min_identifiers: int = rule_config.params.get("min_identifiers", 5)
    severity = rule_config.severity

    result = identifier_token_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
    )

    violations: list[Violation] = []
    for fn in result.functions:
        if fn.total_identifiers < min_identifiers:
            continue
        if fn.mean_tokens > max_mean:
            violations.append(
                Violation(
                    rule="lexical.verbosity",
                    file=fn.file,
                    line=fn.line,
                    symbol=fn.name,
                    message=(
                        f"mean identifier tokens {fn.mean_tokens:.2f} > {max_mean} "
                        f"({fn.total_identifiers} identifiers)"
                    ),
                    severity=severity,
                    value=fn.mean_tokens,
                    threshold=max_mean,
                    metadata={
                        "total_identifiers": fn.total_identifiers,
                        "total_tokens": fn.total_tokens,
                        "end_line": fn.end_line,
                        "language": fn.language,
                    },
                )
            )

    return RuleResult(
        rule="lexical.verbosity",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
