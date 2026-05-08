"""lexical.slackers — sibling functions refusing to align by naming.

Fires on real clusters (functions sharing a first parameter, with
a missing-class or heterogeneous profile per the imposters kernel)
where the member names don't fit a common template. The cluster
is a real family; the names are slacking.

The fix is rename-for-consistency: pick a template
(``verb_param_X``, ``X_param``, etc.) and apply it across the
cluster. This is a review action humans rarely take on
agent-written code, because each name reads fine in isolation —
only as a family do they fail to communicate.
"""
from __future__ import annotations

from pathlib import Path

from slop._lexical.slackers import slackers_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_slackers(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    min_cluster: int = int(rule_config.params.get("min_cluster", 3))
    raw_exempt = rule_config.params.get("exempt_names",
                                        ["self", "cls"])
    exempt_names = frozenset(raw_exempt) if raw_exempt else frozenset()
    max_coverage: float = float(rule_config.params.get("max_coverage", 0.30))
    severity = rule_config.severity

    result = slackers_kernel(
        root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        min_cluster=min_cluster,
        exempt_names=exempt_names,
        max_coverage=max_coverage,
    )

    violations: list[Violation] = []
    for cluster in result.clusters:
        anchor_name, anchor_file, anchor_line = cluster.members[0]
        scope_phrase = (
            f"in `{cluster.scope}`" if cluster.scope_kind == "file"
            else f"under `{cluster.scope}/`" if cluster.scope_kind == "package"
            else "across the codebase"
        )
        member_names = ", ".join(f"`{n}`" for n, _, _ in cluster.members[:5])
        if len(cluster.members) > 5:
            member_names += f" (+{len(cluster.members) - 5})"
        violations.append(Violation(
            rule="lexical.slackers",
            file=anchor_file,
            line=anchor_line,
            symbol=cluster.parameter_name,
            message=(
                f"{len(cluster.members)} functions {scope_phrase} share "
                f"`{cluster.parameter_name}` as first parameter but the "
                f"names don't align ({cluster.coverage:.0%} fit any "
                f"common template). Members: {member_names}. The cluster "
                f"is real; the names refuse to admit it. Consider a "
                f"naming template (e.g., `verb_{cluster.parameter_name}` "
                f"or `{cluster.parameter_name}_attribute`) to make the "
                f"family relationship visible."
            ),
            severity=severity,
            value=round(cluster.coverage, 3),
            threshold=max_coverage,
            metadata={
                "scope": cluster.scope,
                "scope_kind": cluster.scope_kind,
                "profile_from_imposters": cluster.profile_label,
                "coverage": round(cluster.coverage, 3),
                "n_meaningful_patterns": cluster.n_meaningful_patterns,
                "members": [
                    {"name": n, "file": f, "line": l}
                    for n, f, l in cluster.members
                ],
            },
        ))

    return RuleResult(
        rule="lexical.slackers",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "files_searched": result.files_searched,
            "clusters_detected": len(result.clusters),
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
