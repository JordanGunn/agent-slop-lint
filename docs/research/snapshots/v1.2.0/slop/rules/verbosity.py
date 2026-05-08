"""lexical.verbosity — flag function/class names with too many tokens.

A long function or class name compensates for a missing namespace
or class. The smell is structural — the name encodes scope the
codebase doesn't have.
"""
from __future__ import annotations

from pathlib import Path

from slop._lexical.verbosity import verbosity_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_verbosity(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    max_tokens: int = int(rule_config.params.get("max_tokens", 3))
    check_classes: bool = bool(rule_config.params.get("check_classes", True))
    severity = rule_config.severity

    result = verbosity_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        max_tokens=max_tokens,
        check_classes=check_classes,
    )

    violations: list[Violation] = []
    for item in result.items:
        violations.append(Violation(
            rule="lexical.verbosity",
            file=item.file,
            line=item.line,
            symbol=item.name,
            message=(
                f"{item.kind} name `{item.name}` has {item.token_count} tokens "
                f"(> {max_tokens}); consider extracting a namespace or class"
            ),
            severity=severity,
            value=item.token_count,
            threshold=max_tokens,
            metadata={
                "kind": item.kind,
                "tokens": item.tokens,
                "language": item.language,
            },
        ))

    return RuleResult(
        rule="lexical.verbosity",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "items_checked": result.items_analyzed,
            "files_searched": result.files_searched,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
