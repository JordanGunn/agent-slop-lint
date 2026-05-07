"""lexical.imposters — parameters camouflaged as ordinary dependencies.

Flags clusters of functions sharing a first-parameter name. The
parameter LOOKS like an ordinary dependency in each function
signature, but its repeated appearance across N functions reveals
it's acting as a hidden receiver — these functions are de facto
methods on a missing class.

The kernel uses recursive namespace scoping: clusters reported at
the narrowest scope where they cohere. Phase 3 of v1.2 will add
multi-signal scoring (body-shape + receiver-call density + modal
overlap) on top of this kernel for sharper verdict classification.

See ``docs/methods/lexical/multi_criteria_ranking.md``.
"""
from __future__ import annotations

from pathlib import Path

from slop._lexical.imposters import imposters_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_imposters(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Flag missing-receiver candidates from first-parameter clustering."""
    min_cluster: int = int(rule_config.params.get("min_cluster", 3))
    raw_exempt = rule_config.params.get("exempt_names",
                                        ["self", "cls"])
    exempt_names = frozenset(raw_exempt) if raw_exempt else frozenset()
    severity = rule_config.severity

    result = imposters_kernel(
        root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        min_cluster=min_cluster,
        exempt_names=exempt_names,
    )

    violations: list[Violation] = []
    for cluster in result.clusters:
        # Only emit violations for strong candidates by default; weak
        # and false-positive entries inform via the summary but don't
        # become violations.
        if cluster.verdict != "strong":
            continue
        anchor_name, anchor_file, anchor_line = cluster.members[0]
        scope_phrase = (
            f"in `{cluster.scope}`" if cluster.scope_kind == "file"
            else f"under `{cluster.scope}/`" if cluster.scope_kind == "package"
            else "across the codebase"
        )
        violations.append(Violation(
            rule="lexical.imposters",
            file=anchor_file,
            line=anchor_line,
            symbol=cluster.parameter_name,
            message=(
                f"{len(cluster.members)} functions {scope_phrase} share "
                f"`{cluster.parameter_name}` as first parameter. "
                f"{cluster.advisory}"
            ),
            severity=severity,
            metadata={
                "verdict": cluster.verdict,
                "scope": cluster.scope,
                "scope_kind": cluster.scope_kind,
                "members": [
                    {"name": n, "file": f, "line": l}
                    for n, f, l in cluster.members
                ],
                "parameter_types": sorted(cluster.parameter_types),
            },
        ))

    status = "fail" if violations else "pass"
    return RuleResult(
        rule="lexical.imposters",
        status=status,
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "files_searched": result.files_searched,
            "clusters_detected": len(result.clusters),
            "strong_clusters": sum(1 for c in result.clusters if c.verdict == "strong"),
            "weak_clusters": sum(1 for c in result.clusters if c.verdict == "weak"),
            "false_positive_clusters": sum(1 for c in result.clusters if c.verdict == "false_positive"),
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
