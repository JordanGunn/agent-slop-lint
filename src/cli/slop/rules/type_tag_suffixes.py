"""lexical.type_tag_suffixes — flag identifiers whose suffix restates their type."""
from __future__ import annotations

from pathlib import Path

from slop._lexical.type_tag_suffixes import (
    DEFAULT_TAG_TO_TYPES,
    type_tag_suffixes_kernel,
)
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_type_tag_suffixes(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    raw_tags = rule_config.params.get("tag_to_types")
    tag_to_types = (
        {k.lower(): frozenset(str(t) for t in v) for k, v in raw_tags.items()}
        if isinstance(raw_tags, dict)
        else DEFAULT_TAG_TO_TYPES
    )
    severity = rule_config.severity

    result = type_tag_suffixes_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        tag_to_types=tag_to_types,
    )

    violations: list[Violation] = []
    for item in result.items:
        violations.append(Violation(
            rule="lexical.type_tag_suffixes",
            file=item.file,
            line=item.line,
            symbol=item.identifier,
            message=(
                f"`{item.identifier}: {item.annotation}` — suffix `{item.suffix}` "
                f"restates the type `{item.matched_type}`; drop the suffix"
            ),
            severity=severity,
            metadata={
                "function": item.function,
                "suffix": item.suffix,
                "annotation": item.annotation,
                "matched_type": item.matched_type,
                "language": item.language,
            },
        ))

    return RuleResult(
        rule="lexical.type_tag_suffixes",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "files_searched": result.files_searched,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
