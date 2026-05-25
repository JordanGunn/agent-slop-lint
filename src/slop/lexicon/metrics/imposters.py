"""lexical.imposters — parameters camouflaged as ordinary deps.

The view's ``first_param_clusters`` surfaces clusters of functions
sharing a first parameter and labels each cluster with a *profile*:

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
emit violations.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


def _derive_root(lexicon: Lexicon, slop_config: Config) -> Path:
    """Prefer slop_config.root when explicitly set; otherwise fall back
    to the longest common directory across the lexicon's parses."""
    if slop_config.root and slop_config.root != ".":
        return Path(slop_config.root).expanduser().resolve()
    import os
    paths = [p.path for p in lexicon._parses]  # noqa: SLF001
    if paths:
        common = Path(os.path.commonpath([str(p) for p in paths]))
        return common.parent if common.is_file() else common
    if slop_config.root:
        return Path(slop_config.root).expanduser().resolve()
    return Path.cwd()


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
    lexicon: Lexicon,
    rule_config: RuleConfig,
    slop_config: Config,
) -> RuleResult:
    """Flag first-parameter clusters whose profile matches a missing
    class, strategy family, or heterogeneous receiver."""
    min_cluster: int = int(rule_config.params.get("min_cluster", 3))
    raw_exempt = rule_config.params.get("exempt_names", ["self", "cls"])
    exempt_names = frozenset(raw_exempt) if raw_exempt else frozenset()
    severity = rule_config.severity
    root = _derive_root(lexicon, slop_config)

    clusters = lexicon.first_param_clusters(
        min_cluster=min_cluster,
        exempt_names=exempt_names,
        root=root,
    )

    violations: list[Slop] = []
    for cluster in clusters:
        if cluster.profile_label in ("infrastructure", "false_positive", "unknown"):
            continue
        _anchor_name, anchor_file, anchor_line = cluster.members[0]
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
        violations.append(Slop(
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
    for c in clusters:
        profile_counts[c.profile_label] = profile_counts.get(c.profile_label, 0) + 1

    functions_checked = sum(1 for _ in lexicon._callable_by_key)  # noqa: SLF001

    return RuleResult(
        rule="lexical.imposters",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": functions_checked,
            "clusters_detected": len(clusters),
            "profile_counts": profile_counts,
            "violation_count": len(violations),
        },
        errors=[],
    )

RULE = RuleDefinition(
    name=Tag.IMPOSTERS.key,
    category=Tag.IMPOSTERS.key,
    description='Parameters camouflaged as ordinary deps; missing receiver class',
    default_severity='warning',
    default_enabled=True,
    threshold_label='≥ 3 functions sharing param',
    run=run_imposters,
)
