"""Complexity rules — substrate-native threshold checks.

Rules:
  ``structural.complexity.cyclomatic``  — fail if any callable's CCX
                                          exceeds threshold (McCabe 1976).
  ``structural.complexity.cognitive``   — fail if any callable's CogC
                                          exceeds threshold (Campbell 2018).

Both rules are pure threshold-application over ``Structure.cyclomatic``
and ``Structure.cognitive``. All language-specific decision-counting
lives inside the view per the views-own-compute principle; no AST
walking, tree-sitter import, or per-language branching in this module.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.config.models import RuleConfig, SlopConfig
from slop.linter.slop import Slop
from slop.linter.types import RuleResult

if TYPE_CHECKING:
    from slop.structure.view import Structure


def run_cyclomatic(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    """Flag callables whose McCabe cyclomatic complexity exceeds threshold."""
    threshold = rule_config.params.get("cyclomatic_threshold", 10)
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    findings: list[tuple[int, Slop]] = []
    functions_checked = 0
    for c in structure.callables():
        ccx = structure.cyclomatic(c)
        functions_checked += 1
        if ccx > threshold:
            try:
                rel = str(c.path.relative_to(root))
            except ValueError:
                rel = str(c.path)
            findings.append((ccx, Slop(
                rule="structural.complexity.cyclomatic",
                file=rel,
                line=c.line,
                symbol=c.qualname.split(".")[-1],
                message=f"CCX {ccx} exceeds {threshold}",
                severity=severity,
                value=ccx,
                threshold=threshold,
                metadata={"end_line": c.end_line, "qualname": c.qualname},
            )))

    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule="structural.complexity.cyclomatic",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": functions_checked,
            "violation_count": len(violations),
        },
    )


def run_cognitive(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    """Flag callables whose Cognitive Complexity (Campbell 2018) exceeds threshold."""
    threshold = rule_config.params.get("cognitive_threshold", 15)
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    findings: list[tuple[int, Slop]] = []
    functions_checked = 0
    for c in structure.callables():
        cog = structure.cognitive(c)
        functions_checked += 1
        if cog > threshold:
            try:
                rel = str(c.path.relative_to(root))
            except ValueError:
                rel = str(c.path)
            findings.append((cog, Slop(
                rule="structural.complexity.cognitive",
                file=rel,
                line=c.line,
                symbol=c.qualname.split(".")[-1],
                message=f"CogC {cog} exceeds {threshold}",
                severity=severity,
                value=cog,
                threshold=threshold,
                metadata={"end_line": c.end_line, "qualname": c.qualname},
            )))

    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule="structural.complexity.cognitive",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": functions_checked,
            "violation_count": len(violations),
        },
    )
