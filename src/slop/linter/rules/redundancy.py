"""Sibling-callee redundancy — refactoring signal for top-level functions.

Rules:
  ``redundancy``  — flag pairs of sibling top-level
    callables that share a significant number of non-trivial callee
    names.

When two peer functions both call the same set of helpers, the
codebase is signalling either:
  - a missing shared helper that should encapsulate the common calls, or
  - a partial copy of one function into the other with minor variation
    (poor factoring).

Config params
-------------
  min_shared  int    Minimum number of shared non-trivial callees to
                     flag a pair (default: 3).
  min_score   float  Minimum ``|shared| / max(|callees_a|, |callees_b|)``
                     to flag a pair (default: 0.5).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure


def run_redundancy(
    structure: Structure, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag sibling top-level callables with overlapping callee sets."""
    del slop_config
    min_shared = int(rule_config.params.get("min_shared", 3))
    min_score = float(rule_config.params.get("min_score", 0.5))
    severity = rule_config.severity

    pairs = structure.redundant_siblings(
        min_shared=min_shared, min_score=min_score,
    )

    violations: list[Slop] = []
    for pair in pairs:
        shared_preview = ", ".join(pair.shared_callees[:5])
        if len(pair.shared_callees) > 5:
            shared_preview += f" …+{len(pair.shared_callees) - 5} more"
        violations.append(Slop(
            rule="redundancy",
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
                "shared_callees": list(pair.shared_callees),
                "score": pair.score,
            },
        ))

    return RuleResult(
        rule="redundancy",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "pair_violations": len(violations),
            "min_shared": min_shared,
            "min_score": min_score,
        },
    )

RULE = RuleDefinition(
    name=Tag.REDUNDANCY.key,
    category=Tag.REDUNDANCY.key,
    description='Sibling top-level functions sharing non-trivial callees (refactoring signal)',
    default_severity='warning',
    default_enabled=True,
    threshold_label='≥ 3 shared',
    run=run_redundancy,
    scopes=(),
)
