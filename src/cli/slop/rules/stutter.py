"""Lexical stutter rules — three split rules sharing one kernel.

The original ``lexical.stutter`` collapsed three distinct smells into
one rule, which made noisy waivers a near-given because users wanted
to dial down the variant they didn't care about while keeping the
others. v1.1.0 splits the rule into three:

- ``lexical.stutter.namespaces`` — symbol stutters with module path
  (e.g. ``slop.rules.complexity.complexity_kernel``).
- ``lexical.stutter.callers`` — method or attribute name stutters with
  enclosing class (``UserService.get_user_user_id``).
- ``lexical.stutter.identifiers`` — local variable name stutters with
  the enclosing function (``required_binaries`` inside
  ``check_required_binaries``).

Legacy ``lexical.stutter`` keeps working via ``slop._compat`` (which
maps it to ``lexical.stutter.identifiers``, the closest single-rule
match given how the original rule was actually used in practice).
"""
from __future__ import annotations

from pathlib import Path

from slop._lexical.stutter import ALL_SCOPES, stutter_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def _run(
    rule_name: str,
    scope_filter: frozenset[str],
    root: Path,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    min_overlap: int = int(rule_config.params.get("min_overlap_tokens", 2))
    severity = rule_config.severity

    result = stutter_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        scope_filter=scope_filter,
    )

    violations: list[Violation] = []
    for fn in result.functions:
        for v in fn.violations:
            if len(v.overlap) < min_overlap:
                continue
            violations.append(Violation(
                rule=rule_name,
                file=fn.file,
                line=v.line,
                symbol=v.identifier,
                message=(
                    f"identifier '{v.identifier}' repeats tokens {v.overlap} "
                    f"from enclosing {v.scope_type} '{v.scope_name}'"
                ),
                severity=severity,
                value=len(v.overlap),
                threshold=min_overlap,
                metadata={
                    "scope_name": v.scope_name,
                    "scope_type": v.scope_type,
                    "overlap": v.overlap,
                    "identifier_tokens": v.tokens,
                },
            ))

    return RuleResult(
        rule=rule_name,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": len(result.functions),
            "violation_count": len(violations),
        },
        errors=result.errors,
    )


def run_stutter_namespaces(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    return _run("lexical.stutter.namespaces", frozenset({"module"}),
                root, rule_config, slop_config)


def run_stutter_callers(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    return _run("lexical.stutter.callers", frozenset({"class"}),
                root, rule_config, slop_config)


def run_stutter_identifiers(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    return _run("lexical.stutter.identifiers", frozenset({"function"}),
                root, rule_config, slop_config)


def run_stutter(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Legacy unified stutter rule.

    Retained so existing fixtures and tests keep working at the call
    site. ``_compat.LEGACY_RULE_NAMES`` translates ``lexical.stutter``
    in TOML and waivers to ``lexical.stutter.identifiers``; this
    function preserves the old behaviour for code that imports the
    function directly.
    """
    return _run("lexical.stutter", ALL_SCOPES, root, rule_config, slop_config)
