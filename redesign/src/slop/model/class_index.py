"""Corpus-wide class index + CK inheritance/coupling metrics.

CK's DIT/NOC/CBO need cross-class context (the inheritance graph and the set of
known class names), so a ``ClassIndex`` is built once over all carved classes
and attached to each ``Class`` component. Ported from the legacy view CK methods.
Matching is by simple class name, as in the legacy (``extract_superclasses``
yields simple names).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClassIndex:
    known: frozenset[str]
    parent_map: dict[str, list[str]]
    children_map: dict[str, list[str]]
    by_name: dict[str, Any]   # simple name -> a Class component (last wins on clash)


def build(classes: list[Any]) -> ClassIndex:
    """Build the index from all Class components in a corpus."""
    known: set[str] = set()
    parent_map: dict[str, list[str]] = {}
    children_map: dict[str, list[str]] = {}
    by_name: dict[str, Any] = {}
    for cls in classes:
        name = cls.name
        known.add(name)
        by_name[name] = cls
        bases = list(cls._base_names)
        parent_map.setdefault(name, []).extend(bases)
        for base in bases:
            children_map.setdefault(base, []).append(name)
    return ClassIndex(frozenset(known), parent_map, children_map, by_name)


def dit(cls: Any, idx: ClassIndex) -> int:
    """Depth of Inheritance Tree — longest known-parent chain. Cycle-safe."""
    visited: set[str] = set()
    max_depth = 0

    def walk(current: str, depth: int) -> None:
        nonlocal max_depth
        if current in visited:
            return
        visited.add(current)
        max_depth = max(max_depth, depth)
        for parent in idx.parent_map.get(current, []):
            if parent in idx.known:
                walk(parent, depth + 1)

    walk(cls.name, 0)
    return max_depth


def noc(cls: Any, idx: ClassIndex) -> int:
    """Number of Children — direct subclasses declaring this class as a parent."""
    return len(idx.children_map.get(cls.name, []))


def cbo(cls: Any, idx: ClassIndex) -> int:
    """Coupling Between Objects — distinct known-class references in the body."""
    grammar = cls._grammar
    node = cls._node
    content = cls._content
    ident_types = grammar.identifiers()
    class_types = grammar.classes()
    refs: set[str] = set()
    stack = [node]
    while stack:
        cur = stack.pop()
        if cur is not node and cur.type in class_types:
            continue  # nested class — its own metric
        if cur.type in ident_types:
            text = content[cur.start_byte:cur.end_byte].decode("utf-8", errors="replace")
            if text and text[0].isupper():
                refs.add(text)
        stack.extend(reversed(cur.children))
    refs &= idx.known
    for sc in cls._base_names:
        if sc in idx.known:
            refs.add(sc)
    refs.discard(cls.name)
    return len(refs)
