"""Slackers kernel — clusters of functions whose names refuse to align.

When N functions share a first parameter (a real cluster, per the
imposters kernel) but their NAMES don't follow any common token
template, the names are slacking: the family relationship is
real but invisible in the surface vocabulary.

This is distinct from the sprawl smell (closed-alphabet present)
and the imposters smell (cluster present, behavior matters):
slackers fires when the cluster IS structurally meaningful
(missing-class or heterogeneous profile) but the naming refuses
to express it. The fix is "rename to follow a template" before
or alongside any architectural refactor.

Algorithm (PoC v2.4):

1. Get clusters from the imposters kernel.
2. For each cluster, run within-cluster affix-pattern detection on
   the member function names — exactly the algorithm that runs at
   codebase scope in the sprawl kernel, applied at cluster scope.
3. Compute *coverage* = fraction of cluster members that fit any
   meaningful pattern (a pattern with ≥ 2 distinct variants).
4. Fire when:
   - The cluster is a real cluster (profile is ``missing_class``
     or ``heterogeneous`` — not infrastructure / false-positive)
   - Coverage is below the configured threshold (default 30%)

Reference: ``scripts/research/composition_poc_v2/poc4_within_cluster_affix.py``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop._lexical._words import Lexeme
from slop._lexical.imposters import (
    FirstParameterCluster,
    imposters_kernel,
)
from slop._lexical.sprawl import _build_affix_patterns


@dataclass
class SlackerCluster:
    """A cluster whose names refuse to align."""
    parameter_name: str
    members: list[tuple[str, str, int]]   # (name, file, line)
    coverage: float                       # fraction fitting any pattern
    profile_label: str                    # from the source imposters cluster
    scope: str
    scope_kind: str
    n_meaningful_patterns: int


@dataclass
class SlackersResult:
    clusters: list[SlackerCluster] = field(default_factory=list)
    files_searched: int = 0
    functions_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


def _real_cluster(cluster: FirstParameterCluster) -> bool:
    """Is this cluster a real (architecturally interesting) cluster
    we should be checking for naming alignment?"""
    return cluster.profile_label in ("missing_class", "heterogeneous")


def slackers_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    min_cluster: int = 3,
    exempt_names: frozenset[str] = frozenset(),
    max_coverage: float = 0.30,
) -> SlackersResult:
    """Detect cluster members refusing to follow a naming template.

    ``max_coverage`` is the *upper bound* on within-cluster affix
    coverage that triggers a slacker finding. Below the threshold
    means "the names don't follow any template" — that's the
    slacker smell.
    """
    imposters = imposters_kernel(
        root,
        languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
        min_cluster=min_cluster, exempt_names=exempt_names,
    )

    findings: list[SlackerCluster] = []
    for cluster in imposters.clusters:
        if not _real_cluster(cluster):
            continue
        items = [
            Lexeme.of(name, file=file, line=line)
            for name, file, line in cluster.members
        ]
        patterns = _build_affix_patterns(items)
        meaningful = [
            p for p in patterns
            if sum(len(v) for v in p.variants.values()) >= 2
        ]
        covered: set[str] = set()
        for p in meaningful:
            for entity, members in p.variants.items():
                for n, _, _ in members:
                    covered.add(n)
        coverage = len(covered) / len(items) if items else 0.0

        if coverage <= max_coverage:
            findings.append(SlackerCluster(
                parameter_name=cluster.parameter_name,
                members=list(cluster.members),
                coverage=coverage,
                profile_label=cluster.profile_label,
                scope=cluster.scope,
                scope_kind=cluster.scope_kind,
                n_meaningful_patterns=len(meaningful),
            ))

    return SlackersResult(
        clusters=findings,
        files_searched=imposters.files_searched,
        functions_analyzed=imposters.functions_analyzed,
        errors=list(imposters.errors),
    )
