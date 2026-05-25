"""Hotspots rule — wraps Structure.hotspots (view-native).

Rule:
  hotspots  — fail when any file lands in a forbidden quadrant
                        (default: ``hotspot``) over the configured git
                        log window.

Tornhill 2015's churn × complexity framework with the v2.0 LOC-delta
churn proxy. Default window is 14 days — agentic code rot accumulates
in days not months. Widen to 90 days for human-pace repos.
"""

from __future__ import annotations

from pathlib import Path

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.structure.view import Structure


def run_churn_weighted(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: Config,
) -> RuleResult:
    """Threshold-check growth-weighted complexity hotspots."""
    since = rule_config.params.get("since", "14 days ago")
    min_commits = rule_config.params.get("min_commits", 2)
    fail_on_quadrant = set(rule_config.params.get("fail_on_quadrant", ["hotspot"]))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    result = structure.hotspots(root, since=since, min_commits=min_commits)

    violations: list[Slop] = []
    for fh in result.files:
        if fh.quadrant not in fail_on_quadrant:
            continue
        violations.append(Slop(
            rule="hotspots",
            file=fh.file,
            line=None,
            symbol=None,
            message=(
                f"{fh.quadrant} (CCX={fh.sum_ccx}, "
                f"growth=+{fh.loc_delta} LOC, score={fh.hotspot_score:.0f})"
            ),
            severity=severity,
            value=fh.hotspot_score,
            threshold=None,
            metadata={
                "quadrant": fh.quadrant,
                "sum_ccx": fh.sum_ccx,
                "loc_delta": fh.loc_delta,
                "commit_count": fh.commit_count,
                "last_seen": fh.last_seen,
            },
        ))

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
