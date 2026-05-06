"""lexical.boilerplate_docstrings — flag docstrings that restate the function name."""
from __future__ import annotations

from pathlib import Path

from slop._lexical.boilerplate_docstrings import boilerplate_docstrings_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_boilerplate_docstrings(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    raw_extra = rule_config.params.get("extra_stopwords") or []
    extra_stopwords = frozenset(str(s).lower() for s in raw_extra)
    severity = rule_config.severity

    result = boilerplate_docstrings_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        extra_stopwords=extra_stopwords,
    )

    violations: list[Violation] = []
    for item in result.items:
        violations.append(Violation(
            rule="lexical.boilerplate_docstrings",
            file=item.file,
            line=item.line,
            symbol=item.function,
            message=(
                f"docstring \"{item.docstring_first_sentence}\" only "
                f"restates name tokens; either add information or "
                f"drop the docstring"
            ),
            severity=severity,
            metadata={
                "first_sentence": item.docstring_first_sentence,
                "function_tokens": item.function_tokens,
                "docstring_content_tokens": item.docstring_content_tokens,
                "language": item.language,
            },
        ))

    return RuleResult(
        rule="lexical.boilerplate_docstrings",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "functions_with_docstring": result.functions_with_docstring,
            "files_searched": result.files_searched,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
