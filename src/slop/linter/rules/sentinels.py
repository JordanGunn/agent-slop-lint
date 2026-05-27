"""Sentinel-parameter rule — stringly-typed parameters that should be enums.

Rules:
  ``types.sentinels``  — flag function parameters annotated
    ``str`` (or the language's string analogue) with sentinel-shaped
    names (``status``, ``mode``, ``kind``, ``level``, ``format``, …)
    that should use Literal[...] or an Enum.

A stringly-typed parameter is one where the caller must know a magic
string constant from memory or documentation. Python's ``Literal``
and ``enum.Enum`` both solve this while remaining runtime-compatible.

Config params
-------------
  max_cardinality        int   Flag entries where call-site literal
                               cardinality ≤ this value. Set to 0 to
                               flag all sentinel-named string params
                               regardless of call sites (default: 8).
  require_str_annotation bool  Only flag params with explicit string-
                               typed annotation. False also flags
                               untyped sentinel params (default: True).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.linter.tags import Tag
from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure


def run_sentinels(
    structure: Structure, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag functions with stringly-typed sentinel parameters (parameter scope)."""
    del slop_config
    thresholds = rule_config.params.get("thresholds", {}) or {}
    if "parameter" not in thresholds:
        return RuleResult(
            rule=Tag.SENTINELS.key, status="pass", violations=[],
            summary={"candidates_analyzed": 0, "violations": 0},
        )
    max_cardinality = int(thresholds.get("parameter", 8))
    require_annotation = bool(
        rule_config.params.get("require_str_annotation", True),
    )
    severity = rule_config.severity

    candidates = structure.sentinel_parameters(
        require_str_annotation=require_annotation,
    )

    violations: list[Slop] = []
    for entry in candidates:
        if entry.call_site_count > max_cardinality and max_cardinality > 0:
            continue
        annotation_note = "(str)" if entry.annotated else "(untyped)"
        if entry.call_site_count > 0:
            preview = ", ".join(f'"{v}"' for v in entry.call_site_literals[:5])
            if entry.call_site_count > 5:
                preview += "…"
            literal_note = f"{entry.call_site_count} call-site values: {preview}"
        else:
            literal_note = "no call sites found (advisory)"
        violations.append(Slop(
            rule=Tag.SENTINELS.key,
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
                "language": entry.language,
                "call_site_literals": list(entry.call_site_literals),
                "call_site_count": entry.call_site_count,
            },
            scope="parameter",
        ))

    return RuleResult(
        rule=Tag.SENTINELS.key,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "candidates_analyzed": len(candidates),
            "violations": len(violations),
            "max_cardinality": max_cardinality,
        },
    )

RULE = RuleDefinition(
    name=Tag.SENTINELS.key,
    category=Tag.SENTINELS.key,
    description='Function parameters annotated str with sentinel names (status, mode, kind, …)',
    default_severity='warning',
    default_enabled=True,
    threshold_label='≤ 8 values',
    run=run_sentinels,
    scopes=('parameter',),
)
