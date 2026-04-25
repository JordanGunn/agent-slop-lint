"""Halstead rules — wraps slop._structural halstead_kernel.

Rules:
  halstead.volume      — fail if any function's Volume exceeds threshold
  halstead.difficulty  — fail if any function's Difficulty exceeds threshold

Halstead (1977) derived metrics from operator/operand counts:
  Volume     = Length * log2(Vocabulary)   — information content
  Difficulty = (n1/2) * (N2/n2)            — reader cognitive burden
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.halstead import HalsteadResult, halstead_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def _run_halstead(root: Path, config: SlopConfig) -> HalsteadResult:
    return halstead_kernel(
        root=root,
        languages=config.languages or None,
        excludes=config.exclude or None,
    )


def run_volume(root: Path, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult:
    """Check Halstead Volume per function against threshold."""
    threshold = rule_config.params.get("volume_threshold", 1000)
    severity = rule_config.severity

    result = _run_halstead(root, slop_config)

    violations: list[Violation] = []
    for fn in result.functions:
        if fn.volume > threshold:
            violations.append(
                Violation(
                    rule="halstead.volume",
                    file=fn.file,
                    line=fn.line,
                    symbol=fn.name,
                    message=f"Volume {fn.volume:.0f} exceeds {threshold}",
                    severity=severity,
                    value=fn.volume,
                    threshold=threshold,
                    metadata={
                        "difficulty": fn.difficulty,
                        "effort": fn.effort,
                        "vocabulary": fn.vocabulary,
                        "length": fn.length,
                        "end_line": fn.end_line,
                    },
                )
            )

    return RuleResult(
        rule="halstead.volume",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )


def run_difficulty(root: Path, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult:
    """Check Halstead Difficulty per function against threshold."""
    threshold = rule_config.params.get("difficulty_threshold", 30)
    severity = rule_config.severity

    result = _run_halstead(root, slop_config)

    violations: list[Violation] = []
    for fn in result.functions:
        if fn.difficulty > threshold:
            violations.append(
                Violation(
                    rule="halstead.difficulty",
                    file=fn.file,
                    line=fn.line,
                    symbol=fn.name,
                    message=f"Difficulty {fn.difficulty:.1f} exceeds {threshold}",
                    severity=severity,
                    value=fn.difficulty,
                    threshold=threshold,
                    metadata={
                        "volume": fn.volume,
                        "effort": fn.effort,
                        "vocabulary": fn.vocabulary,
                        "length": fn.length,
                        "end_line": fn.end_line,
                    },
                )
            )

    return RuleResult(
        rule="halstead.difficulty",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
