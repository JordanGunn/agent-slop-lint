"""lexical.stutter — names repeating tokens from any enclosing scope.

The hierarchy is checked top-down: every named entity (class,
function, method) is compared against package, module, and
ancestor class/function names; every body identifier inside a
function is compared against the same scope chain.

Per-level toggle parameters dial down specific levels without
splitting the rule. Defaults: all four levels enabled.

This unifies the v1.1.0 ``lexical.stutter.{namespaces, callers,
identifiers}`` split into a single hierarchy-aware rule.

Catches a case the v1.1.0 split missed: method NAMES stuttering
with their class name (e.g. ``class UserService: def
get_user_service_id(self): ...`` — the method name itself
stutters with the class name).
"""
from __future__ import annotations

from pathlib import Path

from slop._lexical.stutter import ALL_LEVELS, stutter_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def _levels_from_config(rule_config: RuleConfig) -> frozenset[str]:
    """Build the active ``levels`` set from per-level toggle params."""
    toggle_keys = {
        "package": "check_packages",
        "module": "check_modules",
        "class": "check_classes",
        "function": "check_functions",
    }
    return frozenset(
        level for level, key in toggle_keys.items()
        if rule_config.params.get(key, True)
    ) or ALL_LEVELS


def run_stutter(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Flag names that stutter with any enabled enclosing-scope level."""
    min_overlap: int = int(rule_config.params.get("min_overlap_tokens", 2))
    severity = rule_config.severity
    levels = _levels_from_config(rule_config)

    result = stutter_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        levels=levels,
    )

    violations: list[Violation] = []
    for v in result.violations:
        if len(v.overlap) < min_overlap:
            continue
        kind = "name" if v.is_entity_name else "identifier"
        violations.append(Violation(
            rule="lexical.stutter",
            file=v.file,
            line=v.line,
            symbol=v.identifier,
            message=(
                f"{kind} `{v.identifier}` stutters with "
                f"enclosing {v.scope_level} `{v.scope_name}` — "
                f"shared tokens {v.overlap}"
            ),
            severity=severity,
            value=len(v.overlap),
            threshold=min_overlap,
            metadata={
                "scope_name": v.scope_name,
                "scope_level": v.scope_level,
                "overlap": v.overlap,
                "tokens": v.tokens,
                "is_entity_name": v.is_entity_name,
                "language": v.language,
            },
        ))

    return RuleResult(
        rule="lexical.stutter",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_searched": result.files_searched,
            "violation_count": len(violations),
            "levels_checked": sorted(levels),
        },
        errors=result.errors,
    )
