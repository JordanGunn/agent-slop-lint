"""Lexical tersity rule.

Rules:
  lexical.tersity  — flag functions where a high fraction of
                      identifiers are ≤ 2 characters long

Tersity acts as a guardrail to ensure identifiers aren't shortened so much
that they become cryptic. While verbosity is the dominant agentic smell,
tersity prevents over-correction into single-letter naming.

Config params
-------------
  max_density      float   Maximum tolerated fraction of short identifiers
                           per function (default: 0.50 = 50 %).
  max_len          int     Identifiers at most this many characters are
                           considered "short" (default: 2).
  min_identifiers  int     Skip functions with fewer identifiers than this
                           (default: 5).
  allow_list       list    Conventional short names excluded from the count.
                           Default: ["i", "j", "k", "x", "y", "z", "ok", "n"].
"""

from __future__ import annotations

from pathlib import Path

from slop._lexical.identifier_tokens import identifier_token_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation

_DEFAULT_ALLOW = frozenset({"i", "j", "k", "x", "y", "z", "ok", "n"})


def run_tersity(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Flag functions where too many identifiers are suspiciously short."""
    max_density: float = float(rule_config.params.get("max_density", 0.50))
    max_len: int = int(rule_config.params.get("max_len", 2))
    min_identifiers: int = int(rule_config.params.get("min_identifiers", 5))
    raw_allow = rule_config.params.get("allow_list", None)
    allow: frozenset[str] = (
        frozenset(raw_allow) if raw_allow is not None else _DEFAULT_ALLOW
    )
    severity = rule_config.severity

    lr = identifier_token_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
    )

    violations: list[Violation] = []

    for fn in lr.functions:
        if fn.total_identifiers < min_identifiers:
            continue

        short = [
            ident for ident in fn.identifiers
            if len(ident) <= max_len and ident not in allow
        ]
        density = len(short) / fn.total_identifiers

        if density > max_density:
            violations.append(
                Violation(
                    rule="lexical.tersity",
                    file=fn.file,
                    line=fn.line,
                    symbol=fn.name,
                    message=(
                        f"{density:.0%} of identifiers in '{fn.name}' are "
                        f"≤{max_len} chars ({len(short)}/{fn.total_identifiers}): "
                        + ", ".join(sorted(set(short)))
                    ),
                    severity=severity,
                    value=round(density, 4),
                    threshold=max_density,
                    metadata={
                        "short_identifiers": sorted(set(short)),
                        "short_count": len(short),
                        "total_identifiers": fn.total_identifiers,
                        "density": round(density, 4),
                    },
                )
            )

    return RuleResult(
        rule="lexical.tersity",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": lr.functions_analyzed,
            "violation_count": len(violations),
        },
        errors=list(lr.errors),
    )
