"""Locus resolution — the narrowest scope containing a set of components.

A finding produced by a corpus-altitude rule is usually *about* a sub-scope: one
entity, or a *group* of them (a cluster, an import cycle, a clone family). For a
group the canonical attribution target is the narrowest scope that owns every
member — the module if they are co-located, the package or realm if they are
spread. ``narrowest_common_ancestor`` walks each member's owner chain (root → leaf)
and returns the deepest scope shared by all of them. For a single scope it returns
that scope. Empty input → ``None``.

Scopes are taken duck-typed (anything exposing ``.owner`` and ``.id``) so this stays
within the metrics layer's contract: ``metrics`` consumes the region surface but never
imports the ``scope`` package.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def narrowest_common_ancestor(scopes: Iterable[Any]) -> Any | None:
    chains: list[list[Any]] = []
    for s in scopes:
        chain: list[Any] = []
        cur: Any = s
        while cur is not None:
            chain.append(cur)
            cur = cur.owner
        chain.reverse()  # root ... leaf
        chains.append(chain)
    if not chains:
        return None
    nca: Any = None
    for depth in range(min(len(c) for c in chains)):
        if len({c[depth].id for c in chains}) != 1:
            break
        nca = chains[0][depth]
    return nca
