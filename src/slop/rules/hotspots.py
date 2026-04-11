"""Hotspots rule — wraps aux hotspots_kernel.

Rules:
  hotspots  — fail if any file lands in a forbidden quadrant
"""

from __future__ import annotations

from pathlib import Path

from aux.kernels.hotspots import hotspots_kernel

from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_churn_weighted(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Check churn-weighted complexity hotspots."""
    since = rule_config.params.get("since", "90 days ago")
    min_commits = rule_config.params.get("min_commits", 2)
    fail_on_quadrant = set(rule_config.params.get("fail_on_quadrant", ["hotspot"]))
    severity = rule_config.severity

    result = hotspots_kernel(
        root=root,
        excludes=slop_config.exclude or None,
        since=since,
        min_commits=min_commits,
    )

    violations: list[Violation] = []
    for fh in result.files:
        if fh.quadrant in fail_on_quadrant:
            violations.append(
                Violation(
                    rule="hotspots",
                    file=fh.file,
                    line=None,
                    symbol=None,
                    message=(
                        f"{fh.quadrant} (CCX={fh.sum_ccx}, "
                        f"churn={fh.change_freq}, score={fh.hotspot_score:.0f})"
                    ),
                    severity=severity,
                    value=fh.hotspot_score,
                    threshold=None,
                    metadata={
                        "quadrant": fh.quadrant,
                        "sum_ccx": fh.sum_ccx,
                        "change_freq": fh.change_freq,
                        "last_seen": fh.last_seen,
                    },
                )
            )

    return RuleResult(
        rule="hotspots",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_analyzed": result.files_analyzed,
            "total_commits": result.total_commits_analyzed,
            "window_since": result.window_since,
            "quadrant_counts": result.quadrant_counts,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
