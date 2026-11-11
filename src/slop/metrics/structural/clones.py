"""Parameterized clone clusters among a set of callables (Baker 1995: a match up to a
consistent renaming of names), where only names the body binds may be renamed.

Operates on duck-typed component objects (``_ast_node()``, ``_grammar``, ``qualname``) so it
does not import the concrete scope classes (avoids a cycle).
"""
from __future__ import annotations

import hashlib
from typing import Any, NamedTuple

from ...ast.binding import SymbolKind
from ..locus import narrowest_common_ancestor
from .records import CloneCluster, CloneMember


def clone_clusters(callables: list[Any], *, min_leaf_nodes: int = 10) -> list[CloneCluster]:
    """Clone clusters among ``callables``: bodies whose leaves match token for token, except
    for what a refactor could pass in as a parameter.

    Every name keeps its text, except a name the callable itself binds (a parameter or a local,
    by its ``slop.ast.binding``), which is replaced by its order of first appearance: renaming
    a local consistently does not hide a clone, but calling a different function, reading a
    different member or passing a different keyword argument is different code. Binding is
    per occurrence, so two locals that share a spelling in different scopes stay distinct.

    A body counts as logic when it has ``min_leaf_nodes`` leaves that are neither literal text
    nor punctuation; its literal values are ignored. A body with fewer logic leaves but
    ``min_leaf_nodes`` literal leaves is a constant table: two tables are clones only if their
    literals are equal. Anything smaller is too small to call a clone."""
    buckets: dict[str, list[tuple[str, int, Any]]] = {}
    for c in callables:
        body = _body_of(c._ast_node(), c._grammar.block_types())
        leaves = _leaves(body, c._grammar, *_bound(c, body))
        literal = sum(1 for leaf in leaves if leaf.literal)
        logic = sum(1 for leaf in leaves if not leaf.literal and leaf.kind not in _PUNCTUATION)
        if logic >= min_leaf_nodes:
            by_value = False
        elif literal >= min_leaf_nodes:
            by_value = True
        else:
            continue
        buckets.setdefault(_fingerprint(leaves, by_value), []).append((c.qualname, len(leaves), c))
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


_PUNCTUATION = frozenset({",", ":", ";", "(", ")", "[", "]", "{", "}"})


class _Leaf(NamedTuple):
    kind: str
    text: str
    #: True when the leaf belongs to a literal (a number, or a string with its quotes)
    literal: bool
    #: the order of first appearance of the name, when the body binds it; else None
    bound: int | None


_BOUND = frozenset({SymbolKind.PARAMETER, SymbolKind.LOCAL})


def _bound(callable_: Any, body: Any) -> tuple[dict[int, int], list[int]]:
    """Which name occurrences in ``callable_`` it binds itself: each occurrence's start byte
    mapped to the byte where its parameter or local is defined, and the callable's own
    parameters (those before ``body``) by definition byte, which is signature order."""
    node = callable_._node
    inside = range(node.start_byte, node.end_byte)
    bindings = callable_.bindings()
    bound = {start: b.definition for start, b in bindings.items()
             if start in inside and b.kind in _BOUND and b.definition in inside}
    parameters = sorted(b.start for b in bindings.values()
                        if b.defines and b.kind is SymbolKind.PARAMETER and node.start_byte <= b.start < body.raw.start_byte)
    return bound, parameters


def _leaves(node: Any, grammar: Any, bound: dict[int, int], parameters: list[int]) -> list[_Leaf]:
    """Leaves in order, with their text, whether they are literal, and their bound-name index.

    Parameters are numbered by their place in the signature, since calling order is behaviour;
    other bound names by their first appearance in the body."""
    literal_types = grammar.numeric_literal_nodes() | grammar.string_literal_nodes()
    order: dict[int, int] = {definition: i for i, definition in enumerate(parameters)}
    stack = [node]
    leaves: list[_Leaf] = []
    while stack:
        n = stack.pop()
        kids = n.children()
        if kids:
            stack.extend(reversed(kids))
            continue
        parent = n.parent
        in_literal = n.type in literal_types or (parent is not None and parent.type in literal_types)
        definition = bound.get(n.raw.start_byte)
        index = order.setdefault(definition, len(order)) if definition is not None else None
        leaves.append(_Leaf(n.type, n.text, in_literal, index))
    return leaves


def _fingerprint(leaves: list[_Leaf], by_value: bool) -> str:
    """Hash of the leaves: a bound name by its index, a literal by its kind (or, in a constant
    table, its text), anything else by its text."""
    parts = []
    for leaf in leaves:
        if leaf.literal:
            parts.append(f"{leaf.kind}={leaf.text}" if by_value else leaf.kind)
        elif leaf.bound is not None:
            parts.append(f"${leaf.bound}")
        else:
            parts.append(leaf.text)
    return hashlib.sha1("\x00".join(parts).encode(), usedforsecurity=False).hexdigest()[:12]
