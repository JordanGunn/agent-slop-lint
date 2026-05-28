"""lexical.confusion — file holds multiple distinct cohesive units.

A file is "confused" when it contains multiple substantive first-
parameter clusters sharing a namespace. The file is doing the work
of multiple cohesive units; the canonical refactor is to split it
along receiver boundaries.

Two corrective actions, discriminated by cross-cluster cohesion
(Jaccard over member-name token sets):

- ``EXTRACT_SUBPACKAGE`` — clusters share a thematic concept
  (high cross-cluster token overlap), suggesting the file's modules
  belong as siblings under a shared namespace.
- ``SPLIT_MODULE`` — clusters are unrelated concerns (low cross-
  cluster token overlap), the file is a true grab-bag.

Adapts Lanza & Marinescu's (2006) detection-strategy framework from
OO classes to module-level free-function code.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.lexicon._tokens import split_tokens
from slop.lexicon.affix import UNIVERSAL_NOISE
from slop.linter.slop import Action, Slop
from slop.linter.types import RuleResult
from slop.tree.records import CallableKind
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


from slop.linter.rules._roots import derive_root as _derive_root


_RULE = Tag.CONFUSION.key

# Cluster profiles that count as "substantive" for confusion detection.
# A cluster is substantive when it represents a real cohesive unit.
# Excluded: false_positive (exempt names), infrastructure (plumbing
# threaded through unrelated functions — not a separate concern).
_SUBSTANTIVE_PROFILES = frozenset({
    "missing_class", "dispatch_family", "strategy_family",
    "heterogeneous",
})


def _functions_per_file(lexicon: Lexicon, root: Path) -> dict[str, int]:
    """Count emittable functions per file-relative path."""
    counts: dict[str, int] = {}
    for c in lexicon.callables():
        if c.kind == CallableKind.LAMBDA:
            continue
        try:
            rel = str(c.path.relative_to(root))
        except ValueError:
            rel = str(c.path)
        counts[rel] = counts.get(rel, 0) + 1
    return counts


def _cluster_token_set(cluster) -> set[str]:
    """Union of lowercased name-tokens across a cluster's members."""
    out: set[str] = set()
    for name, _file, _line in cluster.members:
        for t in split_tokens(name):
            tl = t.lower()
            if tl not in UNIVERSAL_NOISE:
                out.add(tl)
    return out


def _cross_cluster_jaccard(file_clusters: list) -> float:
    """Mean pairwise Jaccard over cluster token sets.

    High mean = clusters share vocabulary = thematic siblings (subpackage).
    Low mean = clusters use disjoint vocabulary = unrelated concerns (split).
    """
    if len(file_clusters) < 2:
        return 0.0
    token_sets = [_cluster_token_set(c) for c in file_clusters]
    pairs: list[float] = []
    for i in range(len(token_sets)):
        for j in range(i + 1, len(token_sets)):
            a, b = token_sets[i], token_sets[j]
            if not a and not b:
                pairs.append(1.0)
            elif not a or not b:
                pairs.append(0.0)
            else:
                pairs.append(len(a & b) / len(a | b))
    return sum(pairs) / len(pairs) if pairs else 0.0


def run(
    lexicon: Lexicon, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag files that hold multiple substantive receiver clusters."""
    min_functions = int(rule_config.params.get("min_functions", 5))
    min_clusters = int(rule_config.params.get("min_clusters", 2))
    min_cluster_size = int(rule_config.params.get("min_cluster_size", 3))
    # New gate: at least N clusters with substantive profiles.
    min_substantive_clusters = int(
        rule_config.params.get(
            "min_substantive_clusters",
            # Legacy param name preserved for back-compat: if older
            # configs specify min_strong_receivers, honour it.
            rule_config.params.get("min_strong_receivers", 2),
        ),
    )
    raw_exempt = rule_config.params.get("exempt_names", ["self", "cls"])
    exempt_names = frozenset(raw_exempt) if raw_exempt else frozenset()
    severity = rule_config.severity
    root = _derive_root(lexicon, slop_config)

    clusters = lexicon.first_param_clusters(
        min_cluster=min_cluster_size,
        exempt_names=exempt_names,
        root=root,
    )

    # Group file-scope clusters by file. Package/root-scope clusters
    # are irrelevant for the file-level rule.
    by_file: dict[str, list] = {}
    for cluster in clusters:
        if cluster.scope_kind != "file":
            continue
        by_file.setdefault(cluster.scope, []).append(cluster)

    functions_per_file = _functions_per_file(lexicon, root)
    files_searched = len(functions_per_file)
    functions_analyzed = sum(functions_per_file.values())

    violations: list[Slop] = []
    for file, file_clusters in by_file.items():
        n_functions = functions_per_file.get(file, 0)
        if n_functions < min_functions:
            continue
        if len(file_clusters) < min_clusters:
            continue
        substantive = [
            c for c in file_clusters
            if c.profile_label in _SUBSTANTIVE_PROFILES
        ]
        if len(substantive) < min_substantive_clusters:
            continue

        cluster_tuples = [
            (c.parameter_name, len(c.members), c.profile_label)
            for c in substantive
        ]
        cluster_summary = ", ".join(
            f"`{p}` ({n}, {label})" for p, n, label in cluster_tuples
        )
        first_cluster = substantive[0]
        line = first_cluster.members[0][2] if first_cluster.members else 1
        cross_cohesion = _cross_cluster_jaccard(substantive)

        # Discriminator: when the module name itself is a single
        # concept-noun (e.g., "diagnostics.py", "loader.py"), it's a
        # thematic umbrella for whatever lives under it — the clusters
        # belong as siblings under that umbrella as a subpackage.
        # Multi-token module names already encode specificity, so a
        # flat sibling split is the natural shape there.
        module_stem = Path(file).stem.lstrip("_")
        stem_tokens = [t for t in split_tokens(module_stem) if t.lower() not in UNIVERSAL_NOISE]
        is_concept_noun = len(stem_tokens) == 1 and len(stem_tokens[0]) >= 4

        if is_concept_noun or cross_cohesion >= 0.15:
            action = Action.EXTRACT_SUBPACKAGE
            prescription = (
                f"Extract `{file}` into a `{module_stem}/` subpackage. "
                f"The file holds {len(substantive)} substantive receiver "
                f"clusters ({cluster_summary}). The module name "
                f"`{module_stem}` is a concept-noun acting as a "
                f"thematic umbrella — the clusters belong as sibling "
                f"modules under that namespace. Dotref will shorten "
                f"the leaf names (`{module_stem}.X.method()` instead "
                f"of `verbose_method_name`)."
            )
        else:
            action = Action.SPLIT_MODULE
            prescription = (
                f"Split `{file}` into sibling modules along receiver "
                f"boundaries. The file holds {len(substantive)} "
                f"substantive receiver clusters ({cluster_summary}) "
                f"with low cross-cluster vocabulary overlap "
                f"(Jaccard {cross_cohesion:.2f}) — unrelated concerns "
                f"sharing a namespace by accident."
            )

        violations.append(Slop(
            rule=_RULE,
            file=file,
            line=line,
            symbol=file,
            message=(
                f"`{file}` holds {n_functions} functions clustering on "
                f"{len(substantive)} substantive receivers "
                f"({cluster_summary}). Cross-cluster vocabulary Jaccard "
                f"is {cross_cohesion:.2f}. The file is doing the work of "
                f"multiple cohesive units; split along receiver boundaries."
            ),
            severity=severity,
            value=len(substantive),
            threshold=min_substantive_clusters,
            action=action,
            prescription=prescription,
            confidence=0.7 if len(substantive) >= 3 else 0.6,
            metadata={
                "function_count": n_functions,
                "clusters": [
                    {"param": p, "members": n, "profile": label}
                    for p, n, label in cluster_tuples
                ],
                "cross_cluster_jaccard": round(cross_cohesion, 3),
            },
        ))

    return RuleResult(
        rule=_RULE,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_searched": files_searched,
            "functions_checked": functions_analyzed,
            "candidate_files": len(by_file),
            "violation_count": len(violations),
        },
        errors=[],
    )


RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description='File holds multiple substantive receiver clusters (split into siblings or extract subpackage)',
    default_severity='warning',
    default_enabled=True,
    threshold_label='≥ 2 substantive clusters × ≥ 3 members',
    run=run,
)
