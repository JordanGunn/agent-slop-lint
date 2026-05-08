"""Class-level rules — wraps the vendored ck_kernel.

Rules:
  structural.class.coupling                — CBO exceeds threshold
  structural.class.inheritance.depth       — DIT exceeds threshold
  structural.class.inheritance.children    — NOC exceeds threshold
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.ck import ck_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def _run_ck(root: Path, slop_config: SlopConfig):
    """Call ck_kernel once (shared by all class rules)."""
    return ck_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
    )


def run_coupling(root: Path, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult:
    threshold = rule_config.params.get("threshold", 8)
    severity = rule_config.severity
    result = _run_ck(root, slop_config)

    violations: list[Violation] = []
    for cm in result.classes:
        if cm.cbo > threshold:
            violations.append(
                Violation(
                    rule="structural.class.coupling",
                    file=cm.file,
                    line=cm.line,
                    symbol=cm.name,
                    message=f"CBO {cm.cbo} exceeds {threshold} ({cm.kind})",
                    severity=severity,
                    value=cm.cbo,
                    threshold=threshold,
                    metadata={"kind": cm.kind, "dit": cm.dit, "noc": cm.noc, "wmc": cm.wmc},
                )
            )

    return RuleResult(
        rule="structural.class.coupling",
        status="fail" if violations else "pass",
        violations=violations,
        summary={"classes_checked": result.classes_analyzed, "violation_count": len(violations)},
        errors=list(result.errors),
    )


def run_inheritance_depth(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    threshold = rule_config.params.get("threshold", 4)
    severity = rule_config.severity
    result = _run_ck(root, slop_config)

    violations: list[Violation] = []
    for cm in result.classes:
        if cm.dit > threshold:
            violations.append(
                Violation(
                    rule="structural.class.inheritance.depth",
                    file=cm.file,
                    line=cm.line,
                    symbol=cm.name,
                    message=f"DIT {cm.dit} exceeds {threshold} ({cm.kind})",
                    severity=severity,
                    value=cm.dit,
                    threshold=threshold,
                    metadata={"kind": cm.kind, "superclasses": cm.superclasses},
                )
            )

    return RuleResult(
        rule="structural.class.inheritance.depth",
        status="fail" if violations else "pass",
        violations=violations,
        summary={"classes_checked": result.classes_analyzed, "violation_count": len(violations)},
        errors=list(result.errors),
    )


def run_inheritance_children(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    threshold = rule_config.params.get("threshold", 10)
    severity = rule_config.severity
    result = _run_ck(root, slop_config)

    violations: list[Violation] = []
    for cm in result.classes:
        if cm.noc > threshold:
            violations.append(
                Violation(
                    rule="structural.class.inheritance.children",
                    file=cm.file,
                    line=cm.line,
                    symbol=cm.name,
                    message=f"NOC {cm.noc} exceeds {threshold} ({cm.kind})",
                    severity=severity,
                    value=cm.noc,
                    threshold=threshold,
                    metadata={"kind": cm.kind},
                )
            )

    return RuleResult(
        rule="structural.class.inheritance.children",
        status="fail" if violations else "pass",
        violations=violations,
        summary={"classes_checked": result.classes_analyzed, "violation_count": len(violations)},
        errors=list(result.errors),
    )
