"""Combinatorial complexity rule — NPath, view-native.

Wraps ``Structure.combinatorial`` (Nejmeh 1988) in a threshold-application
rule. No AST walking, no tree-sitter import, no per-language branching
at the rule layer — all of that lives in the view.

Renamed from ``structural.complexity.npath`` to
``structural.complexity.combinatorial`` to emphasise what NPath
distinguishes from cyclomatic: the *multiplicative* explosion of paths
through sequential branching, not just the count of decision points.
"""
from __future__ import annotations

from pathlib import Path

from slop.config.models import RuleConfig, SlopConfig
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.structure.view import Structure


def run_combinatorial(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    """Threshold-check per-function NPath against the configured limit."""
    threshold = rule_config.params.get("combinatorial_threshold", 400)
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    findings: list[tuple[int, Slop]] = []
    functions_checked = 0
    for c in structure.callables():
        np = structure.combinatorial(c)
        functions_checked += 1
        if np > threshold:
            try:
                rel = str(c.path.relative_to(root))
            except ValueError:
                rel = str(c.path)
            findings.append((np, Slop(
                rule="structural.complexity.combinatorial",
                file=rel,
                line=c.line,
                symbol=c.qualname.split(".")[-1],
                message=f"NPath {np} exceeds {threshold}",
                severity=severity,
                value=np,
                threshold=threshold,
                metadata={"end_line": c.end_line, "qualname": c.qualname},
            )))

    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule="structural.complexity.combinatorial",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": functions_checked,
            "violation_count": len(violations),
        },
        errors=[],
    )
