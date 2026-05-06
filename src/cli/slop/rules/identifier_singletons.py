"""lexical.identifier_singletons — flag functions where most locals are write-once-read-once."""
from __future__ import annotations

from pathlib import Path

from slop._lexical.identifier_singletons import identifier_singletons_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_identifier_singletons(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    min_locals: int = int(rule_config.params.get("min_locals", 4))
    max_singleton_fraction: float = float(
        rule_config.params.get("max_singleton_fraction", 0.6)
    )
    severity = rule_config.severity

    result = identifier_singletons_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        min_locals=min_locals,
        max_singleton_fraction=max_singleton_fraction,
    )

    violations: list[Violation] = []
    for item in result.items:
        violations.append(Violation(
            rule="lexical.identifier_singletons",
            file=item.file,
            line=item.line,
            symbol=item.function,
            message=(
                f"{len(item.singleton_locals)}/{item.locals_count} locals "
                f"used exactly once "
                f"({item.singleton_fraction:.0%}); consider inlining"
            ),
            severity=severity,
            value=item.singleton_fraction,
            threshold=max_singleton_fraction,
            metadata={
                "locals_count": item.locals_count,
                "singleton_locals": item.singleton_locals,
                "language": item.language,
            },
        ))

    return RuleResult(
        rule="lexical.identifier_singletons",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "files_searched": result.files_searched,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
