"""Stringly-typed parameter rule — wraps stringly_typed_kernel.

Rules:
  structural.types.sentinels  — flag function parameters annotated ``str``
                               with sentinel names (status, mode, kind, …)
                               that should use Literal[...] or an Enum.

A stringly-typed parameter is one where the caller must know a magic string
constant from memory or documentation.  Python's ``Literal`` type annotation
and ``enum.Enum`` both solve this while remaining runtime-compatible.

Config params
-------------
  max_cardinality        int    Flag entries where call-site literal
                                cardinality ≤ this value.  Set to 0 to flag
                                all sentinel-named str params regardless of
                                call sites (default: 8).
  require_str_annotation bool   Only flag params with explicit ``str``
                                annotation (default: True).
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.stringly_typed import stringly_typed_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_stringly_typed(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Flag functions with stringly-typed sentinel parameters."""
    max_cardinality: int = int(rule_config.params.get("max_cardinality", 8))
    require_annotation: bool = bool(
        rule_config.params.get("require_str_annotation", True)
    )
    severity = rule_config.severity

    result = stringly_typed_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        max_cardinality=max_cardinality,
        require_str_annotation=require_annotation,
    )

    violations: list[Violation] = []
    for entry in result.entries:
        # Report when: no call sites found, OR cardinality ≤ max_cardinality
        if entry.call_site_count > max_cardinality and max_cardinality > 0:
            continue  # Too many distinct values → not clearly an enum candidate

        annotation_note = "(str)" if entry.annotated else "(untyped)"
        literal_note = (
            f"{entry.call_site_count} call-site values: "
            + ", ".join(f'"{v}"' for v in entry.call_site_literals[:5])
            + ("…" if len(entry.call_site_literals) > 5 else "")
            if entry.call_site_count > 0
            else "no call sites found (advisory)"
        )
        violations.append(
            Violation(
                rule="structural.types.sentinels",
                file=entry.file,
                line=entry.param_line,
                symbol=entry.function_name,
                message=(
                    f"'{entry.function_name}' parameter '{entry.param_name}' "
                    f"{annotation_note} looks stringly-typed — "
                    f"consider Literal[...] or Enum. {literal_note}"
                ),
                severity=severity,
                value=entry.call_site_count,
                threshold=max_cardinality,
                metadata={
                    "param_name": entry.param_name,
                    "annotated": entry.annotated,
                    "call_site_literals": entry.call_site_literals,
                    "call_site_count": entry.call_site_count,
                },
            )
        )

    return RuleResult(
        rule="structural.types.sentinels",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_analyzed": result.functions_analyzed,
            "files_searched": result.files_searched,
            "violations": len(violations),
            "max_cardinality": max_cardinality,
        },
        errors=list(result.errors),
    )
