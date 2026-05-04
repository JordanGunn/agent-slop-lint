"""Sibling call redundancy rule — wraps sibling_call_redundancy_kernel.

Rules:
  structural.redundancy  — flag pairs of sibling top-level
                                        functions that share a significant
                                        number of non-trivial callee names.

When two peer functions both call the same set of helpers, it is likely that:
  - A new shared helper should extract the common calls, or
  - One function is a partial copy of the other with only minor variation
    (poor factoring).

Config params
-------------
  min_shared  int    Minimum number of shared non-trivial callees to flag
                     a pair (default: 3).
  min_score   float  Minimum |shared| / max(|callees_a|, |callees_b|) to flag
                     a pair (default: 0.5).
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.sibling_calls import sibling_call_redundancy_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_sibling_call_redundancy(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Flag sibling function pairs with high callee overlap."""
    min_shared: int = int(rule_config.params.get("min_shared", 3))
    min_score: float = float(rule_config.params.get("min_score", 0.5))
    severity = rule_config.severity

    result = sibling_call_redundancy_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        min_shared=min_shared,
        min_score=min_score,
    )

    violations: list[Violation] = []
    for pair in result.pairs:
        shared_preview = ", ".join(pair.shared_callees[:5])
        if len(pair.shared_callees) > 5:
            shared_preview += f" …+{len(pair.shared_callees) - 5} more"
        violations.append(
            Violation(
                rule="structural.redundancy",
                file=pair.file,
                line=pair.fn_a_line,
                symbol=pair.fn_a,
                message=(
                    f"'{pair.fn_a}' (line {pair.fn_a_line}) and "
                    f"'{pair.fn_b}' (line {pair.fn_b_line}) share "
                    f"{len(pair.shared_callees)} callees "
                    f"(score {pair.score:.0%}): {shared_preview}"
                ),
                severity=severity,
                value=pair.score,
                threshold=min_score,
                metadata={
                    "fn_a": pair.fn_a,
                    "fn_b": pair.fn_b,
                    "fn_a_line": pair.fn_a_line,
                    "fn_b_line": pair.fn_b_line,
                    "shared_callees": pair.shared_callees,
                    "score": pair.score,
                },
            )
        )

    return RuleResult(
        rule="structural.redundancy",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_analyzed": result.functions_analyzed,
            "files_searched": result.files_searched,
            "pair_violations": len(violations),
            "min_shared": min_shared,
            "min_score": min_score,
        },
        errors=list(result.errors),
    )
