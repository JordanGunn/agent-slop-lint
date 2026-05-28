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

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Action, Slop
from slop.linter.types import RuleResult
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


from slop.linter.rules._roots import derive_root as _derive_root


_RULE = Tag.IMPOSTERS.key

def _action_for_cluster(cluster) -> tuple[Action, str, float]:
    """Map a cluster's profile + battery signals to (action, prescription, confidence).

    The battery dimensions:
    - profile (receiver_density × body_cohesion)
    - is_isolate × file_spread (distribution position)
    - scope_hapax_ratio (vocabulary fragmentation)
    """
    param = cluster.parameter_name
    n = len(cluster.members)

    if cluster.profile_label == "missing_class":
        # Tiny near-clone clusters (small + very high cohesion) are
        # framework boilerplate — each member calls a few methods on a
        # framework-provided receiver (argparse subparsers, tree-sitter
        # cursors, FastAPI routers). Class extraction wraps the third-
        # party object; a helper function deduplicates without wrapping.
        if n <= 5 and cluster.body_jaccard_mean >= 0.7:
            prescription = (
                f"Extract a `register_{param}(...)` helper function. "
                f"{n} functions share `{param}` as receiver with near-"
                f"clone cohesion (Jaccard "
                f"{cluster.body_jaccard_mean:.2f}). Bodies are nearly "
                f"identical — framework boilerplate. A helper "
                f"deduplicates without wrapping the underlying receiver "
                f"type."
            )
            return (Action.EXTRACT_HELPER, prescription, 0.75)
        # Otherwise: clean class extraction.
        prescription = (
            f"Extract a class with `{param}` as `self`. {n} functions "
            f"actively call methods on `{param}` (density "
            f"{cluster.mean_receiver_calls:.1f}) and share structural "
            f"shape (cohesion {cluster.body_jaccard_mean:.2f}). Scope "
            f"hapax is {cluster.scope_hapax_ratio:.2f}."
        )
        # Confidence boosted by clean scope (low hapax), reduced by
        # fragmenting scope (high hapax — extract in a fragmenting scope
        # may not stick).
        confidence = 0.75 if cluster.scope_hapax_ratio < 0.4 else 0.55
        return (Action.EXTRACT_CLASS, prescription, confidence)

    if cluster.profile_label == "strategy_family":
        prescription = (
            f"Accept as a strategy family or replace with a dispatch "
            f"table. {n} functions are structural clones operating on "
            f"`{param}` (cohesion {cluster.body_jaccard_mean:.2f}). Do "
            f"NOT extract as methods — the polymorphism happens through "
            f"data, not through `self`."
        )
        return (Action.NOTE_PATTERN, prescription, 0.85)

    if cluster.profile_label == "dispatch_family":
        prescription = (
            f"Verify the dispatch pattern is intentional. {n} functions "
            f"call methods on `{param}` independently (density "
            f"{cluster.mean_receiver_calls:.1f}, cohesion "
            f"{cluster.body_jaccard_mean:.2f}). This is a registry/"
            f"plugin family — leave as functions unless subsets share "
            f"internal logic."
        )
        return (Action.REVIEW_INTENT, prescription, 0.6)

    # heterogeneous
    prescription = (
        f"Review the cluster's membership. {n} functions share `{param}` "
        f"but profile is mixed (cohesion {cluster.body_jaccard_mean:.2f}, "
        f"receiver density {cluster.mean_receiver_calls:.1f}). Some "
        f"members may be unrelated helpers; relocate them before "
        f"deciding on a refactor."
    )
    return (Action.REVIEW_INTENT, prescription, 0.4)


_PROFILE_MESSAGES = {
    "missing_class": (
        "{n} functions {scope_phrase} share `{param}` as first "
        "parameter; receiver-call density {rc:.1f} per member, "
        "body cohesion {bj:.2f}. Members actively treat `{param}` "
        "as a receiver — extract a class with `{param}` as ``self``."
    ),
    "dispatch_family": (
        "{n} functions {scope_phrase} share `{param}` as first "
        "parameter; receiver-call density {rc:.1f} per member, but "
        "body cohesion is {bj:.2f} (low). Members call methods on "
        "`{param}` independently — this is a plugin/dispatch family, "
        "not a missing class. Look for subsets that share internal "
        "logic and could be grouped."
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


def run(
    lexicon: Lexicon,
    rule_config: Rule,
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
        if cluster.is_isolate and cluster.file_spread > 0:
            message += (
                f" `{cluster.parameter_name}` is a packet-isolate token "
                f"(spread across {cluster.file_spread} files, bonds with "
                f"no specific partner)."
            )
        if cluster.scope_hapax_ratio >= 0.5:
            message += (
                f" Scope hapax_ratio is {cluster.scope_hapax_ratio:.2f} — "
                f"vocabulary in the enclosing scope is fragmenting; the "
                f"cluster sits in a broader naming-coherence problem."
            )
        action, prescription, confidence = _action_for_cluster(cluster)
        violations.append(Slop(
            rule="lexical.imposters",
            file=anchor_file,
            line=anchor_line,
            symbol=cluster.parameter_name,
            message=message,
            severity=severity,
            action=action,
            prescription=prescription,
            confidence=confidence,
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
                "is_isolate": cluster.is_isolate,
                "file_spread": cluster.file_spread,
                "scope_hapax_ratio": round(cluster.scope_hapax_ratio, 3),
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
    name=_RULE,
    category=_RULE,
    description='Parameters camouflaged as ordinary deps; missing receiver class',
    default_severity='warning',
    default_enabled=True,
    threshold_label='≥ 3 functions sharing param',
    run=run,
)
