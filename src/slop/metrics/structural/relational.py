"""Relational measures over a set of callables — sibling-callee redundancy,
intra-module call-islands, and type-2 clone clusters. Ported from the legacy
redundancy / intra_file_call_components / clones compute.

Operates on duck-typed component objects (``_node``/``_content``/``_grammar``,
``_iter_callables()``, ``name``, ``kind``, ``KIND``) so it does not import the
concrete classes (avoids a cycle).
"""
from __future__ import annotations

import hashlib
from collections import Counter
from itertools import combinations
from typing import Any

from ...identity import CallableKind, ScopeKind
from ..locus import narrowest_common_ancestor
from .records import CallIsland, CloneCluster, RedundancyPair


def callees_of(comp: Any) -> frozenset[str]:
    """Meaningful callee names in a callable's body (length>=3, no special methods,
    no builtins).

    The grammar supplies the language's builtin set and its implicit-dispatch
    special-method rule as *facts*; discounting them as noise is this consumer's
    policy decision."""
    grammar = comp._grammar
    call_types = grammar.call_node_types()
    if not call_types:
        return frozenset()
    builtins = grammar.language_builtins()
    node = comp._ast_node()
    body = node.field("body") or node
    out: set[str] = set()
    for n in body.walk():
        if n.type in call_types:
            name = grammar.extract_callee_name(n.raw, comp._content)
            if name is not None and _meaningful(name, builtins, grammar):
                out.add(name)
    return frozenset(out)


def _meaningful(name: str, builtins: frozenset[str], grammar: Any) -> bool:
    return (len(name) >= 3
            and not (grammar is not None and grammar.is_special_method(name))
            and name not in builtins)


def ubiquitous_callees(corpus: Any, *, threshold: float = 0.25, min_calls: int = 3) -> frozenset[str]:
    """Project callees called by more than ``threshold`` of all functions corpus-wide —
    the project's own 'stdlib' (a colour palette, a logging shim). They are project-defined
    so they survive the ``callable_names`` filter, but they inflate sibling-redundancy
    overlap exactly as language builtins do: two functions sharing only ``dim``/``yellow``
    are not sharing a *helper*. Same keyness idea as ``lexical.cohesion`` — high
    document-frequency carries no signal. ``min_calls`` keeps a tiny corpus from flagging a
    callee used twice."""
    funcs = [c for c in corpus._iter_callables() if c.kind == CallableKind.FUNCTION]
    n = len(funcs)
    if n == 0:
        return frozenset()
    df: Counter = Counter()
    for c in funcs:
        df.update(callees_of(c))
    return frozenset(name for name, count in df.items()
                     if count >= min_calls and count / n > threshold)


def redundant_siblings(module: Any, *, min_shared: int = 3, min_score: float = 0.5,
                       exclude: frozenset[str] = frozenset()) -> list[RedundancyPair]:
    """Top-level sibling functions sharing >= min_shared non-trivial callees.

    Precision: a shared callee only counts if it names a *project-defined* callable
    (the corpus-wide ``callable_names`` index on the analysis-context). Without this,
    ubiquitous stdlib methods (``.strip``/``.decode``/``.split``) inflate the overlap
    and the rule penalises DRY — two functions that both call ``.strip()`` are not
    sharing a helper. Builtins are already discounted in ``callees_of``; this removes
    the rest of the stdlib-method noise. With no project-name index (a module built
    without a carve context), it falls back to the unfiltered overlap. ``exclude``
    additionally drops ubiquitous *project* callees (see ``ubiquitous_callees``).
    """
    ctx = getattr(module, "context", None)
    project_names = ctx.callable_names if ctx is not None else None

    funcs = [
        c for c in module.children()
        if c.KIND == ScopeKind.CALLABLE and c.kind == CallableKind.FUNCTION
    ]
    data = [(c.name, callees_of(c)) for c in funcs]
    data = [(n, s) for n, s in data if s]
    out: list[RedundancyPair] = []
    for (na, sa), (nb, sb) in combinations(data, 2):
        shared = sa & sb
        if project_names:
            shared = {c for c in shared if c in project_names}
        if exclude:
            shared = {c for c in shared if c not in exclude}
        if len(shared) < min_shared:
            continue
        if len(shared) / max(len(sa), len(sb)) < min_score:
            continue
        out.append(RedundancyPair(left=na, right=nb, shared_callees=tuple(sorted(shared))))
    return out


def call_islands(module: Any) -> list[CallIsland]:
    """Connected components of the module's intra-module call graph (by simple
    name). Each callable is in exactly one island; isolated ones are singletons."""
    callables = list(module._iter_callables())
    names = {c.name for c in callables}
    parent = {n: n for n in names}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for c in callables:
        caller = c.name
        for callee in callees_of(c):
            if callee in names and callee != caller:
                parent[find(callee)] = find(caller)

    groups: dict[str, set[str]] = {}
    for n in names:
        groups.setdefault(find(n), set()).add(n)
    return [CallIsland(members=tuple(sorted(g))) for g in groups.values()]


def clone_clusters(callables: list[Any], *, min_leaf_nodes: int = 10) -> list[CloneCluster]:
    """Type-2 clone clusters among ``callables`` — bodies sharing an AST
    leaf-type fingerprint (identifiers/literals discarded)."""
    buckets: dict[str, list[tuple[str, int, Any]]] = {}
    for c in callables:
        body = _body_of(c._ast_node(), c._grammar.block_types())
        leaves = _leaf_types(body)
        if len(leaves) < min_leaf_nodes:
            continue
        buckets.setdefault(_fingerprint(leaves), []).append((c.qualname, len(leaves), c))
    clusters: list[CloneCluster] = []
    for members in buckets.values():
        if len(members) < 2:
            continue
        nca = narrowest_common_ancestor([m[2] for m in members])
        clusters.append(CloneCluster(
            members=tuple(sorted(m[0] for m in members)),
            leaf_count=members[0][1],
            locus=nca.id if nca is not None else None,
        ))
    clusters.sort(key=lambda cl: -len(cl.members))
    return clusters


def _body_of(node: Any, block_types: frozenset[str]) -> Any:
    if not block_types:
        return node
    for child in node.children():
        if child.type in block_types:
            return child
    return node


def _leaf_types(node: Any) -> list[str]:
    stack = [node]
    leaves: list[str] = []
    while stack:
        n = stack.pop()
        kids = n.children()
        if kids:
            stack.extend(reversed(kids))
        else:
            leaves.append(n.type)
    return leaves


def _fingerprint(leaves: list[str]) -> str:
    return hashlib.sha1(",".join(leaves).encode(), usedforsecurity=False).hexdigest()[:12]
