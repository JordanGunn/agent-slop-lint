"""Type-2 clone clusters among a set of callables.

Operates on duck-typed component objects (``_ast_node()``, ``_grammar``, ``qualname``) so it
does not import the concrete scope classes (avoids a cycle).
"""
from __future__ import annotations

import hashlib
from typing import Any, NamedTuple

from ..locus import narrowest_common_ancestor
from .records import CloneCluster, CloneMember


def clone_clusters(callables: list[Any], *, min_leaf_nodes: int = 10) -> list[CloneCluster]:
    """Type-2 clone clusters among ``callables``: bodies sharing an AST leaf-type
    fingerprint, with identifier names and literal values discarded.

    One kind of identifier keeps its name: a member assigned through a receiver
    (``self.x = ...``). It names state the object defines, which a different body cannot
    share by renaming, so constructors that store different fields are not clones.

    A body counts as logic when it has ``min_leaf_nodes`` leaves that are neither literal
    text nor punctuation. A body with fewer logic leaves but ``min_leaf_nodes`` literal
    leaves is a constant table: two tables are clones only if their literals are equal.
    Anything smaller is too small to call a clone."""
    buckets: dict[str, list[tuple[str, int, Any]]] = {}
    for c in callables:
        body = _body_of(c._ast_node(), c._grammar.block_types())
        leaves = _leaves(body, c._grammar)
        literal = sum(1 for leaf in leaves if leaf.literal is not None)
        logic = sum(1 for leaf in leaves if leaf.literal is None and leaf.kind not in _PUNCTUATION)
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
    #: the text, when the leaf belongs to a literal (a number, or a string with its quotes)
    literal: str | None
    #: the member name, when the leaf names a member assigned through a receiver
    member: str | None


def _leaves(node: Any, grammar: Any) -> list[_Leaf]:
    """Leaves in order, each with its literal text or stored-member name where it has one."""
    literal_types = grammar.numeric_literal_nodes() | grammar.string_literal_nodes()
    access, assigning = grammar.member_access(), grammar.assignment_nodes()
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
        stored = _is_stored_member(n, parent, access, assigning)
        leaves.append(_Leaf(n.type, n.text if in_literal else None, n.text if stored else None))
    return leaves


def _is_stored_member(leaf: Any, parent: Any, access: Any, assigning: Any) -> bool:
    """True when ``leaf`` is the member name of ``receiver.member`` on the left of an assignment."""
    if access is None or not assigning or parent is None or parent.type != access.node_type:
        return False
    if parent.field(access.member_field) != leaf:
        return False
    assignment = parent.parent
    return assignment is not None and assignment.type in assigning and assignment.field("left") == parent


def _fingerprint(leaves: list[_Leaf], by_value: bool) -> str:
    """Hash of the leaf types, plus stored-member names, plus (for a constant table) literals."""
    parts = []
    for leaf in leaves:
        part = leaf.kind
        if leaf.member is not None:
            part += f"@{leaf.member}"
        if by_value and leaf.literal is not None:
            part += f"={leaf.literal}"
        parts.append(part)
    return hashlib.sha1(",".join(parts).encode(), usedforsecurity=False).hexdigest()[:12]
