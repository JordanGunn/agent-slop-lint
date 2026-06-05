"""Cross-rule corroboration for inferred lexical clusters (disposition policy).

An inferred first-parameter cluster (imposters/slackers) is a claim-free OBSERVATION on
its own — slop cannot honestly assert the refactor from names alone. But when an
*independent structural signal* binds the same functions — a Type-2 clone family or a
redundant-sibling pair — the inferred shape is corroborated, which licenses promoting the
finding to a REVIEW verdict (still WARNING-capped, remedy open). One signal stays an
observation; corroboration is what earns the verdict. This realises the
"verdict-only-when-corroborated" rung of the disposition policy.

Cost note: ``corroboration_groups`` recomputes clone families (corpus-wide) and
redundant-sibling pairs (per module); imposters and slackers each build it once per run.
A future optimisation is to memoise it on the corpus analysis-context, since
``structure.duplication`` / ``structure.redundancy`` compute the same data.
"""
from __future__ import annotations

from typing import Any, Iterator

from ..metrics.structural.view import Structure
from ..scope.identity import ScopeKind


def _modules(component: Any) -> Iterator[Any]:
    if component.KIND == ScopeKind.MODULE:
        yield component
        return
    for child in component.children():
        yield from _modules(child)


def corroboration_groups(component: Any, *, min_leaf_nodes: int = 10) -> list[frozenset[str]]:
    """Groups of function (leaf) names that an independent structural signal binds:
    Type-2 clone families (corpus-wide) and redundant-sibling pairs (per module). A
    first-parameter cluster whose member names overlap one group by >=2 is corroborated.
    Leaf-name matching is approximate, but the >=2 requirement guards against collision.

    Memoised on the corpus AnalysisContext: imposters and slackers both need this index,
    and computing it walks clone detection + every module's redundancy, so it is built
    once per run and shared (keyed by ``min_leaf_nodes``)."""
    ctx = getattr(component, "context", None)
    key = ("corroboration_groups", min_leaf_nodes)
    if ctx is not None and key in ctx.cache:
        return ctx.cache[key]

    groups: list[frozenset[str]] = []
    for family in Structure.over(component).clone_clusters(min_leaf_nodes=min_leaf_nodes):
        groups.append(frozenset(m.split(".")[-1] for m in family.members))
    for module in _modules(component):
        for pair in Structure.over(module).redundant_siblings():
            groups.append(frozenset({pair.left, pair.right}))

    if ctx is not None:
        ctx.cache[key] = groups
    return groups


def is_corroborated(member_names: set[str], groups: list[frozenset[str]]) -> bool:
    """True if some structural group shares >=2 members with this cluster — i.e. an
    independent signal binds at least two of the cluster's functions."""
    return any(len(member_names & g) >= 2 for g in groups)
