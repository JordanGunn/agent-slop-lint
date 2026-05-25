"""Clone-density rule — Type-2 clone detection on the Structure view.

Rules:
  ``duplication``  — flag codebases where a significant
    fraction of callables are Type-2 clones (structurally identical
    bodies with different identifiers).

Config params
-------------
  threshold        float   Maximum tolerated clone fraction (0.0–1.0).
                           Default: 0.05 (5 % of functions may be cloned).
  min_leaf_nodes   int     Minimum AST leaf count for a callable to be
                           considered; skips trivial one-liner bodies.
                           Default: 10.
  min_cluster_size int     Only report clusters of at least this many
                           members. Default: 2.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure

DEFAULT_THRESHOLD = 0.05
DEFAULT_MIN_LEAF_NODES = 10
DEFAULT_MIN_CLUSTER_SIZE = 2
PRECISION = 4


def run_clone_density(
    structure: Structure, rule_config: RuleConfig, slop_config: Config,
) -> RuleResult:
    """Flag codebase-level clone density and individual clone clusters."""
    del slop_config
    params = rule_config.params
    threshold = float(params.get("threshold", DEFAULT_THRESHOLD))
    min_leaf_nodes = int(params.get("min_leaf_nodes", DEFAULT_MIN_LEAF_NODES))
    min_cluster_size = int(params.get("min_cluster_size", DEFAULT_MIN_CLUSTER_SIZE))
    severity = rule_config.severity

    report = structure.clones(min_leaf_nodes=min_leaf_nodes)
    reportable = [c for c in report.clusters if c.size >= min_cluster_size]

    violations: list[Slop] = []
    for cluster in reportable:
        first = cluster.members[0]
        others = ", ".join(f"{m.file}:{m.line}" for m in cluster.members[1:])
        violations.append(Slop(
            rule="duplication",
            file=first.file,
            line=first.line,
            symbol=first.name,
            message=(
                f"function '{first.name}' is a Type-2 clone "
                f"(fingerprint {cluster.fingerprint}) — also at: {others}"
            ),
            severity=severity,
            value=cluster.size,
            threshold=min_cluster_size,
            metadata={
                "fingerprint": cluster.fingerprint,
                "clone_count": cluster.size,
                "members": [
                    {"file": m.file, "line": m.line, "name": m.name}
                    for m in cluster.members
                ],
            },
        ))

    if report.clone_fraction > threshold and report.functions_analyzed > 0:
        pct = report.clone_fraction * 100
        violations.insert(0, Slop(
            rule="duplication",
            file=".",
            line=None,
            symbol=None,
            message=(
                f"clone density {pct:.1f}% exceeds threshold "
                f"{threshold * 100:.1f}% "
                f"({sum(c.size for c in reportable)} cloned functions "
                f"across {len(reportable)} clusters)"
            ),
            severity=severity,
            value=report.clone_fraction,
            threshold=threshold,
            metadata={
                "functions_analyzed": report.functions_analyzed,
                "clone_fraction": report.clone_fraction,
                "cluster_count": len(reportable),
            },
        ))

    return RuleResult(
        rule="duplication",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_analyzed": report.functions_analyzed,
            "clone_clusters": len(reportable),
            "clone_fraction": round(report.clone_fraction, PRECISION),
            "threshold": threshold,
        },
    )

RULE = RuleDefinition(
    name=Tag.DUPLICATION.key,
    category=Tag.DUPLICATION.key,
    description='Type-2 clone detection: structurally identical function bodies',
    default_severity='warning',
    default_enabled=True,
    threshold_label='> 5%',
    run=run_clone_density,
    scopes=(),
)
