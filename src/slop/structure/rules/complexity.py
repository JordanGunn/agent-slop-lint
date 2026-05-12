"""Complexity rules — wraps the vendored ccx_kernel and ck_kernel.

Rules:
  structural.complexity.cyclomatic    — fail if any function's CCX exceeds threshold
  structural.complexity.cognitive     — fail if any function's CogC exceeds threshold
  structural.class.complexity          — fail if any class's WMC exceeds threshold
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.ccx import CcxResult, ccx_kernel
from slop._structural.ck import ck_kernel
from slop.structure.view import Structure
from slop.linter.slop import Slop
from slop.config.models import RuleConfig, SlopConfig
from slop.linter.types import RuleResult
from slop.linter.slop import Slop


def _run_ccx(root: Path, config: SlopConfig) -> CcxResult:
    """Call ccx_kernel once and return the result (shared by both rules)."""
    return ccx_kernel(
        root=root,
        languages=config.languages or None,
        excludes=config.exclude or None,
    )


def run_cyclomatic(root: Path, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult:
    """Check cyclomatic complexity per function against threshold."""
    threshold = rule_config.params.get("cyclomatic_threshold", 10)
    severity = rule_config.severity

    result = _run_ccx(root, slop_config)

    violations: list[Slop] = []
    for fn in result.functions:
        if fn.ccx > threshold:
            violations.append(
                Slop(
                    rule="structural.complexity.cyclomatic",
                    file=fn.file,
                    line=fn.line,
                    symbol=fn.name,
                    message=f"CCX {fn.ccx} exceeds {threshold} ({fn.zone})",
                    severity=severity,
                    value=fn.ccx,
                    threshold=threshold,
                    metadata={"zone": fn.zone, "cog": fn.cog, "end_line": fn.end_line},
                )
            )

    return RuleResult(
        rule="structural.complexity.cyclomatic",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )


def run_cyclomatic_v2(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    """v2 cyclomatic — pure threshold-application over view's compute.

    No AST walking, no tree-sitter import, no per-language branching.
    All language-specific decision-counting lives inside
    ``Structure.cyclomatic`` (per the views-own-compute principle).
    """
    threshold = rule_config.params.get("cyclomatic_threshold", 10)
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    findings: list[tuple[int, Slop]] = []
    functions_checked = 0
    for c in structure.callables():
        ccx = structure.cyclomatic(c)
        functions_checked += 1
        if ccx > threshold:
            # Emit relative path to match the legacy formatter's expectation.
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

    # Sort by CCX descending to match legacy ccx_kernel ordering.
    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule="structural.complexity.cyclomatic",
        status="fail" if violations else "pass",
        violations=violations,  # type: ignore[arg-type]  # Slop+Slop coexist during migration
        summary={
            "functions_checked": functions_checked,
            "violation_count": len(violations),
        },
        errors=[],
    )


def run_cognitive(root: Path, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult:
    """Check cognitive complexity per function against threshold."""
    threshold = rule_config.params.get("cognitive_threshold", 15)
    severity = rule_config.severity

    result = _run_ccx(root, slop_config)

    violations: list[Slop] = []
    for fn in result.functions:
        if fn.cog > threshold:
            violations.append(
                Slop(
                    rule="structural.complexity.cognitive",
                    file=fn.file,
                    line=fn.line,
                    symbol=fn.name,
                    message=f"CogC {fn.cog} exceeds {threshold}",
                    severity=severity,
                    value=fn.cog,
                    threshold=threshold,
                    metadata={"zone": fn.zone, "ccx": fn.ccx, "end_line": fn.end_line},
                )
            )

    return RuleResult(
        rule="structural.complexity.cognitive",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )


def run_cognitive_v2(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    """v2 cognitive — pure threshold-application over the view's compute.

    No AST walking, no tree-sitter import, no per-language branching.
    All language-specific nesting-aware decision-counting lives inside
    ``Structure.cognitive`` (Campbell 2018).
    """
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
        errors=[],
    )


def run_weighted(root: Path, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult:
    """Check Weighted Methods per Class (WMC) against threshold."""
    threshold = rule_config.params.get("threshold", 40)
    severity = rule_config.severity

    result = ck_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
    )

    violations: list[Slop] = []
    for cm in result.classes:
        if cm.wmc > threshold:
            violations.append(
                Slop(
                    rule="structural.class.complexity",
                    file=cm.file,
                    line=cm.line,
                    symbol=cm.name,
                    message=(
                        f"WMC {cm.wmc} exceeds {threshold} "
                        f"({cm.method_count} methods, {cm.kind})"
                    ),
                    severity=severity,
                    value=cm.wmc,
                    threshold=threshold,
                    metadata={"kind": cm.kind, "method_count": cm.method_count, "cbo": cm.cbo},
                )
            )

    return RuleResult(
        rule="structural.class.complexity",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "classes_checked": result.classes_analyzed,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
