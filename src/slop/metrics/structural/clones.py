"""Type-2 clone clusters among a set of callables.

Operates on duck-typed component objects (``_ast_node()``, ``_grammar``, ``qualname``) so it
does not import the concrete scope classes (avoids a cycle).
"""
from __future__ import annotations

import hashlib
from typing import Any

from ..locus import narrowest_common_ancestor
from .records import CloneCluster, CloneMember


def clone_clusters(callables: list[Any], *, min_leaf_nodes: int = 10) -> list[CloneCluster]:
    """Type-2 clone clusters among ``callables``: bodies sharing an AST leaf-type
    fingerprint, with identifier names and literal values discarded. A body that is mostly
    literals is data, not logic (a constant table), and two data bodies are clones only if
    their literals are equal."""
    buckets: dict[str, list[tuple[str, int, Any]]] = {}
    for c in callables:
        body = _body_of(c._ast_node(), c._grammar.block_types())
        leaves = _leaves(body, c._grammar)
        if len(leaves) < min_leaf_nodes:
            continue
        buckets.setdefault(_fingerprint(leaves), []).append((c.qualname, len(leaves), c))
    clusters: list[CloneCluster] = []
    for members in buckets.values():
        if len(members) < 2:
            continue
        nca = narrowest_common_ancestor([m[2] for m in members])
        clusters.append(CloneCluster(
            members=tuple(sorted(
                (CloneMember(scope=m[2].id, qualname=m[0], line=m[2].line) for m in members),
                key=lambda cm: (cm.scope.spans[0].path if cm.scope.spans else "", cm.line, cm.qualname))),
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


def _leaves(node: Any, grammar: Any) -> list[tuple[str, str | None]]:
    """Leaf node types in order, each with its text when the leaf belongs to a literal (a
    number, or a string with its quotes and content)."""
    literal_types = grammar.numeric_literal_nodes() | grammar.string_literal_nodes()
    stack = [node]
    leaves: list[tuple[str, str | None]] = []
    while stack:
        n = stack.pop()
        kids = n.children()
        if kids:
            stack.extend(reversed(kids))
            continue
        parent = n.parent
        in_literal = n.type in literal_types or (parent is not None and parent.type in literal_types)
        leaves.append((n.type, n.text if in_literal else None))
    return leaves


def _fingerprint(leaves: list[tuple[str, str | None]]) -> str:
    """Hash of the leaf types; a mostly-literal body also hashes its literal text."""
    is_data = sum(1 for _, text in leaves if text is not None) * 2 > len(leaves)
    parts = [f"{kind}={text}" if is_data and text is not None else kind for kind, text in leaves]
    return hashlib.sha1(",".join(parts).encode(), usedforsecurity=False).hexdigest()[:12]
