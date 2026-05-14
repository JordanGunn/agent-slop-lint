"""Type-2 clone detection — structurally identical callable bodies.

Two callables are Type-2 clones when the leaf-node-type sequences of
their body subtrees hash to the same SHA-1 prefix. Identifier names
and literal values are discarded; only the structural shape matters.

Substrate-aligned port of the legacy ``clone_density_kernel``: same
algorithm, but iterates the Structure view's callables and consults
``Language.block_types()`` for the body wrapper, so no per-language
function-node / body-wrapper tables live inside the helper.
"""
from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from slop.structure.records import CloneCluster, CloneMember, CloneReport

if TYPE_CHECKING:
    from slop.structure.view import Structure


def compute_clones(
    structure: Structure,
    *,
    min_leaf_nodes: int = 10,
) -> CloneReport:
    """Group callables into Type-2 clone clusters.

    Iterates ``structure.callables()``; for each callable retrieves its
    AST node from the view's internal index, descends into the body
    via the grammar's ``block_types()`` set, collects the leaf-type
    sequence, and hashes it. Clusters with size < 2 are dropped.
    """
    from slop.language.grammars import LANGUAGE_BY_ID

    buckets: dict[str, list[CloneMember]] = {}
    total = 0

    for callable_record in structure.callables():
        path_str = str(callable_record.path)
        key = (path_str, callable_record.qualname)
        node = structure._node_by_key.get(key)
        if node is None:
            continue
        total += 1

        language = structure._language_by_path.get(path_str)
        if language is None:
            continue
        lang_cls = LANGUAGE_BY_ID.get(language)
        if lang_cls is None:
            continue

        body = _body_of(node, lang_cls.block_types())
        leaves = _leaf_types(body)
        if len(leaves) < min_leaf_nodes:
            continue

        fingerprint = _fingerprint(leaves)
        short_name = callable_record.qualname.rsplit(".", 1)[-1]
        member = CloneMember(
            file=path_str,
            name=short_name,
            line=callable_record.line,
            end_line=callable_record.end_line,
            language=language,
            fingerprint=fingerprint,
        )
        buckets.setdefault(fingerprint, []).append(member)

    clusters: list[CloneCluster] = []
    for fp, members in buckets.items():
        if len(members) < 2:
            continue
        ordered = tuple(sorted(members, key=lambda m: (m.file, m.line)))
        clusters.append(CloneCluster(fingerprint=fp, size=len(ordered), members=ordered))
    clusters.sort(key=lambda c: -c.size)

    cloned_count = sum(c.size for c in clusters)
    fraction = cloned_count / total if total else 0.0
    return CloneReport(
        clusters=tuple(clusters),
        functions_analyzed=total,
        clone_fraction=fraction,
    )


def _body_of(node, block_types: frozenset[str]):
    """Return the body-wrapper child of a callable node, falling back to the node itself."""
    if not block_types:
        return node
    for child in node.children:
        if child.type in block_types:
            return child
    return node


def _leaf_types(node) -> list[str]:
    """Iterative DFS — return the type of every leaf node in pre-order."""
    stack = [node]
    leaves: list[str] = []
    while stack:
        n = stack.pop()
        children = n.children
        if children:
            stack.extend(reversed(children))
        else:
            leaves.append(n.type)
    return leaves


def _fingerprint(leaves: list[str]) -> str:
    h = hashlib.sha1(",".join(leaves).encode(), usedforsecurity=False)
    return h.hexdigest()[:12]
