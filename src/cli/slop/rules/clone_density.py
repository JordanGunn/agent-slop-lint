"""Clone-density rule — wraps clone_density_kernel.

Rules:
  structural.duplication  — flag codebases where a significant fraction of
                              functions are Type-2 clones (structurally
                              identical bodies with different identifiers).

Config params
-------------
  threshold       float   Maximum tolerated clone fraction (0.0–1.0).
                          Default: 0.05 (5 % of functions may be cloned).
  min_leaf_nodes  int     Minimum AST leaf count for a function to be
                          considered; skips trivial one-liner bodies.
                          Default: 10.
  min_cluster_size int    Only report clusters of at least this many members.
                          Default: 2.
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.clone_density import clone_density_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation

DEFAULT_THRESHOLD = 0.05
DEFAULT_MIN_LEAF_NODES = 10
DEFAULT_MIN_CLUSTER_SIZE = 2
PRECISION = 4


def run_clone_density(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Flag codebase-level clone density and individual clone clusters."""
    params = rule_config.params
    threshold: float = float(params.get("threshold", DEFAULT_THRESHOLD))
    min_leaf_nodes: int = int(params.get("min_leaf_nodes", DEFAULT_MIN_LEAF_NODES))
    min_cluster_size: int = int(params.get("min_cluster_size", DEFAULT_MIN_CLUSTER_SIZE))
    severity = rule_config.severity

    result = clone_density_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        min_leaf_nodes=min_leaf_nodes,
    )

    # Filter clusters by min_cluster_size
    reportable = [
        cluster for cluster in result.clusters if cluster.size >= min_cluster_size
    ]

    violations: list[Violation] = []

    # One violation per clone cluster (file-level; line points to first member)
    for cluster in reportable:
        first = cluster.members[0]
        others = ", ".join(
            f"{m.file}:{m.line}" for m in cluster.members[1:]
        )
        violations.append(
            Violation(
                rule="structural.duplication",
                file=first.file,
                line=first.line,
                symbol=first.name,
                message=(
                    f"function '{first.name}' is a Type-2 clone "
                    f"(fingerprint {cluster.fingerprint}) — "
                    f"also at: {others}"
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
            )
        )

    # Also emit a summary violation when the overall density exceeds threshold
    if result.clone_fraction > threshold and result.functions_analyzed > 0:
        pct = result.clone_fraction * 100
        violations.insert(
            0,
            Violation(
                rule="structural.duplication",
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
                value=result.clone_fraction,
                threshold=threshold,
                metadata={
                    "functions_analyzed": result.functions_analyzed,
                    "clone_fraction": result.clone_fraction,
                    "cluster_count": len(reportable),
                },
            ),
        )

    status = "fail" if violations else "pass"
    return RuleResult(
        rule="structural.duplication",
        status=status,
        violations=violations,
        summary={
            "functions_analyzed": result.functions_analyzed,
            "files_searched": result.files_searched,
            "clone_clusters": len(reportable),
            "clone_fraction": round(result.clone_fraction, PRECISION),
            "threshold": threshold,
        },
        errors=list(result.errors),
    )
