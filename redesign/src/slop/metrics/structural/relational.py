"""Relational measures over a set of callables — sibling-callee redundancy,
intra-module call-islands, and type-2 clone clusters. Ported from the legacy
redundancy / intra_file_call_components / clones compute.

Operates on duck-typed component objects (``_node``/``_content``/``_grammar``,
``_iter_callables()``, ``name``, ``kind``, ``KIND``) so it does not import the
concrete classes (avoids a cycle).
"""
from __future__ import annotations

import hashlib
from itertools import combinations
from typing import Any

from ...identity import CallableKind, ComponentKind
from .records import CallIsland, CloneCluster, RedundancyPair


def callees_of(comp: Any) -> frozenset[str]:
    """Meaningful callee names in a callable's body (length>=3, no dunders, no builtins).

    The grammar supplies the language's builtin set as a *fact*; discounting them
    as noise is this consumer's policy decision."""
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
            if name is not None and _meaningful(name, builtins):
                out.add(name)
    return frozenset(out)


def _meaningful(name: str, builtins: frozenset[str]) -> bool:
    return len(name) >= 3 and not (name.startswith("__") and name.endswith("__")) and name not in builtins


def redundant_siblings(module: Any, *, min_shared: int = 3, min_score: float = 0.5) -> list[RedundancyPair]:
    """Top-level sibling functions sharing >= min_shared non-trivial callees."""
    funcs = [
        c for c in module.children()
        if c.KIND == ComponentKind.CALLABLE and c.kind == CallableKind.FUNCTION
    ]
    data = [(c.name, callees_of(c)) for c in funcs]
    data = [(n, s) for n, s in data if s]
    out: list[RedundancyPair] = []
    for (na, sa), (nb, sb) in combinations(data, 2):
        shared = sa & sb
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
    buckets: dict[str, list[tuple[str, int]]] = {}
    for c in callables:
        body = _body_of(c._ast_node(), c._grammar.block_types())
        leaves = _leaf_types(body)
        if len(leaves) < min_leaf_nodes:
            continue
        buckets.setdefault(_fingerprint(leaves), []).append((c.qualname, len(leaves)))
    clusters: list[CloneCluster] = []
    for members in buckets.values():
        if len(members) < 2:
            continue
        clusters.append(CloneCluster(
            members=tuple(sorted(m[0] for m in members)),
            leaf_count=members[0][1],
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
