"""lexical.weasel_words — flag catchall identifier vocabulary against a banlist."""
from __future__ import annotations

from pathlib import Path

from slop._lexical.weasel_words import (
    DEFAULT_PROFILE,
    WeaselTerm,
    weasel_words_kernel,
)
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def _terms_from_config(rule_config: RuleConfig) -> tuple[WeaselTerm, ...]:
    """Parse user-provided terms (a list of dicts) into ``WeaselTerm``
    tuples. Falls back to the default profile if no override given."""
    raw = rule_config.params.get("terms")
    if not raw:
        return DEFAULT_PROFILE
    parsed: list[WeaselTerm] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        word = entry.get("word")
        positions = entry.get("positions") or ["suffix"]
        if not word:
            continue
        parsed.append(WeaselTerm(
            word=str(word),
            positions=tuple(str(p) for p in positions),
            severity=entry.get("severity"),
            exempt_when=tuple(str(e) for e in (entry.get("exempt_when") or ())),
        ))
    return tuple(parsed) if parsed else DEFAULT_PROFILE


def run_weasel_words(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    default_severity = rule_config.severity
    terms = _terms_from_config(rule_config)

    result = weasel_words_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        terms=terms,
        default_severity=default_severity,
    )

    violations: list[Violation] = []
    for item in result.items:
        violations.append(Violation(
            rule="lexical.weasel_words",
            file=item.file,
            line=item.line,
            symbol=item.name,
            message=(
                f"{item.kind} `{item.name}` matches weasel-word "
                f"`{item.matched_word}` ({item.matched_position}); "
                f"the term carries no semantic content"
            ),
            severity=item.severity,
            metadata={
                "matched_word": item.matched_word,
                "matched_position": item.matched_position,
                "kind": item.kind,
                "language": item.language,
            },
        ))

    return RuleResult(
        rule="lexical.weasel_words",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "items_checked": result.items_analyzed,
            "files_searched": result.files_searched,
            "terms_loaded": len(terms),
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
