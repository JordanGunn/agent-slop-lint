"""lexical.imposters — parameters camouflaged as ordinary deps.

The kernel surfaces clusters of functions sharing a first
parameter and labels each cluster with a *profile*:

- ``missing_class`` — members actively use the parameter as a
  receiver (high attribute-access density). Class extraction is
  the textbook refactor.
- ``strategy_family`` — members are body-shape clones with
  parametric variation; receiver-call density is zero. The
  cluster IS doing one thing N ways. Don't extract a class —
  consider a tabular dispatch (or accept as idiomatic free
  functions).
- ``heterogeneous`` — cluster is real (shared input) but body
  cohesion is low and receiver-calls are sparse. Surface for
  review without prescribing a refactor.
- ``infrastructure`` / ``false_positive`` — preserved verdicts
  for parameters like ``root: Path`` (configuration) or
  ``node: ASTNode`` (third-party type). No advisory.

Only ``missing_class`` and (mildly) ``strategy_family`` profiles
emit violations. The strategy_family case is itself a finding,
but its message corrects the v1.1.0 mistake of recommending
class extraction for color-py-style dispatch families.
"""
from __future__ import annotations

from pathlib import Path

from slop._lexical.imposters import imposters_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


_PROFILE_MESSAGES = {
    "missing_class": (
        "{n} functions {scope_phrase} share `{param}` as first "
        "parameter; receiver-call density {rc:.1f} per member, "
        "body cohesion {bj:.2f}. Members actively treat `{param}` "
        "as a receiver — extract a class with `{param}` as ``self``."
    ),
    "strategy_family": (
        "{n} functions {scope_phrase} share `{param}` as first "
        "parameter; body cohesion {bj:.2f} (clone family) but "
        "receiver-call density is {rc:.1f}. Members are doing the "
        "same thing parametrically — consider a dispatch table or "
        "accept as idiomatic free functions. Do NOT extract as "
        "methods on a class."
    ),
    "heterogeneous": (
        "{n} functions {scope_phrase} share `{param}` as first "
        "parameter; body cohesion {bj:.2f}, receiver-call density "
        "{rc:.1f}. Cluster is real but profile is mixed — review "
        "whether all members belong, or whether helpers should be "
        "moved out before deciding on a refactor."
    ),
}


def run_imposters(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Flag parameter clusters; profile each by body-shape + receiver-call density."""
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
        # Suppress non-actionable profiles (infrastructure, false_positive)
        # and unknown (which only happens when the cluster has fewer than
        # 2 members with body data — rare).
        if cluster.profile_label in (
            "infrastructure", "false_positive", "unknown",
        ):
            continue
        anchor_name, anchor_file, anchor_line = cluster.members[0]
        scope_phrase = (
            f"in `{cluster.scope}`" if cluster.scope_kind == "file"
            else f"under `{cluster.scope}/`" if cluster.scope_kind == "package"
            else "across the codebase"
        )
        message = _PROFILE_MESSAGES.get(
            cluster.profile_label,
            "{n} functions share `{param}` as first parameter.",
        ).format(
            n=len(cluster.members),
            scope_phrase=scope_phrase,
            param=cluster.parameter_name,
            rc=cluster.mean_receiver_calls,
            bj=cluster.body_jaccard_mean,
        )
        violations.append(Violation(
            rule="lexical.imposters",
            file=anchor_file,
            line=anchor_line,
            symbol=cluster.parameter_name,
            message=message,
            severity=severity,
            metadata={
                "profile": cluster.profile_label,
                "verdict": cluster.verdict,
                "scope": cluster.scope,
                "scope_kind": cluster.scope_kind,
                "body_jaccard_mean": round(cluster.body_jaccard_mean, 3),
                "mean_receiver_calls": round(cluster.mean_receiver_calls, 2),
                "modal_overlap_mean": round(cluster.modal_overlap_mean, 3),
                "members": [
                    {"name": n, "file": f, "line": l}
                    for n, f, l in cluster.members
                ],
                "parameter_types": sorted(cluster.parameter_types),
            },
        ))

    profile_counts: dict[str, int] = {}
    for c in result.clusters:
        profile_counts[c.profile_label] = profile_counts.get(c.profile_label, 0) + 1

    return RuleResult(
        rule="lexical.imposters",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "files_searched": result.files_searched,
            "clusters_detected": len(result.clusters),
            "profile_counts": profile_counts,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
