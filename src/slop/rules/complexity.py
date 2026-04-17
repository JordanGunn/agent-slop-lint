"""Complexity rules — wraps aux ccx_kernel and ck_kernel.

Rules:
  complexity.cyclomatic  — fail if any function's CCX exceeds threshold
  complexity.cognitive   — fail if any function's CogC exceeds threshold
  complexity.weighted    — fail if any class's WMC exceeds threshold
"""

from __future__ import annotations

from pathlib import Path

from slop._aux.kernels.ccx import CcxResult, ccx_kernel
from slop._aux.kernels.ck import ck_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


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

    violations: list[Violation] = []
    for fn in result.functions:
        if fn.ccx > threshold:
            violations.append(
                Violation(
                    rule="complexity.cyclomatic",
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
        rule="complexity.cyclomatic",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )


def run_cognitive(root: Path, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult:
    """Check cognitive complexity per function against threshold."""
    threshold = rule_config.params.get("cognitive_threshold", 15)
    severity = rule_config.severity

    result = _run_ccx(root, slop_config)

    violations: list[Violation] = []
    for fn in result.functions:
        if fn.cog > threshold:
            violations.append(
                Violation(
                    rule="complexity.cognitive",
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
        rule="complexity.cognitive",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )


def run_weighted(root: Path, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult:
    """Check Weighted Methods per Class (WMC) against threshold."""
    threshold = rule_config.params.get("weighted_threshold", 50)
    severity = rule_config.severity

    result = ck_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
    )

    violations: list[Violation] = []
    for cm in result.classes:
        if cm.wmc > threshold:
            violations.append(
                Violation(
                    rule="complexity.weighted",
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
        rule="complexity.weighted",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "classes_checked": result.classes_analyzed,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
