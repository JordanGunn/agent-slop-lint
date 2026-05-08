"""lexical.cowards — flag identifiers ending in disambiguator suffixes.

The artifact of failure to commit: ``_v1``/``_v2``, ``_old``/``_new``,
``_local``/``_alt``. The codebase couldn't pick one, so it kept both,
marked with arbitrary suffixes that obscure what actually differs.
"""
from __future__ import annotations

from pathlib import Path

from slop._lexical.cowards import (
    DEFAULT_ALPHA_SUFFIXES,
    cowards_kernel,
)
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_cowards(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    raw_alpha = rule_config.params.get("alpha_suffixes")
    alpha_suffixes = (
        frozenset(s.lower() for s in raw_alpha)
        if raw_alpha is not None
        else DEFAULT_ALPHA_SUFFIXES
    )
    min_stem_tokens: int = int(rule_config.params.get("min_stem_tokens", 1))
    severity = rule_config.severity

    result = cowards_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        alpha_suffixes=alpha_suffixes,
        min_stem_tokens=min_stem_tokens,
    )

    violations: list[Violation] = []
    for item in result.items:
        violations.append(Violation(
            rule="lexical.cowards",
            file=item.file,
            line=item.line,
            symbol=item.name,
            message=(
                f"function `{item.name}` ends in disambiguator `{item.suffix}` "
                f"({item.kind}); the codebase couldn't commit — "
                f"either pick one or describe what differs"
            ),
            severity=severity,
            metadata={
                "suffix": item.suffix,
                "kind": item.kind,
                "language": item.language,
            },
        ))

    return RuleResult(
        rule="lexical.cowards",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "files_searched": result.files_searched,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
