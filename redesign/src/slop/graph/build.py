"""Concrete DependencyGraph — Module-level import edges over a Corpus.

Implements ``slop.graph.dependency.DependencyGraph``. Nodes are Module
ComponentIds; edges come from each Module's raw imports resolved against a
corpus name index (ported from the legacy structure/imports.py). Cycles via
Tarjan SCC. Neighbour-set accessors (beyond the ABC's count-returning
afferent/efferent) support Package-level contraction for Martin metrics.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..identity import ScopeId, ScopeKind, Span
from .dependency import DependencyCycle
from .dependency import DependencyEdge, DependencyGraph
from .imports import module_imports


class ConcreteDependencyGraph(DependencyGraph):
    def __init__(
        self,
        edges: tuple[DependencyEdge, ...],
        efferent: dict[ScopeId, frozenset[ScopeId]],
        afferent: dict[ScopeId, frozenset[ScopeId]],
        label: dict[ScopeId, str],
    ) -> None:
        self._edges = edges
        self._efferent = efferent
        self._afferent = afferent
        self._label = label

    def edges(self):
        return self._edges

    def afferent(self, node: ScopeId) -> int:
        return len(self._afferent.get(node, frozenset()))

    def efferent(self, node: ScopeId) -> int:
        return len(self._efferent.get(node, frozenset()))

    def efferent_nodes(self, node: ScopeId) -> frozenset[ScopeId]:
        return self._efferent.get(node, frozenset())

    def afferent_nodes(self, node: ScopeId) -> frozenset[ScopeId]:
        return self._afferent.get(node, frozenset())

    def cycles(self):
        # Tarjan SCC over the efferent map; components with >1 node are cycles.
        index = 0
        indexes: dict[ScopeId, int] = {}
        lowlink: dict[ScopeId, int] = {}
        stack: list[ScopeId] = []
        on_stack: set[ScopeId] = set()
        out: list[DependencyCycle] = []

        def strongconnect(v: ScopeId) -> None:
            nonlocal index
            indexes[v] = lowlink[v] = index
            index += 1
            stack.append(v)
            on_stack.add(v)
            for w in self._efferent.get(v, frozenset()):
                if w not in indexes:
                    strongconnect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], indexes[w])
            if lowlink[v] == indexes[v]:
                comp: list[ScopeId] = []
                while stack:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                if len(comp) > 1:
                    out.append(DependencyCycle(members=tuple(sorted(self._label[c] for c in comp))))

        for v in self._efferent:
            if v not in indexes:
                strongconnect(v)
        return out


def build(corpus: Any) -> ConcreteDependencyGraph:
    modules = list(_iter_modules(corpus))
    label: dict[ScopeId, str] = {m.id: m.qualname for m in modules}
    module_ids = set(label)
    index: dict[str, ScopeId] = {}
    for m in modules:
        if not m.files:
            continue
        for name in _module_names_for_path(m.files[0]):
            index.setdefault(name, m.id)

    efferent: dict[ScopeId, set[ScopeId]] = {m.id: set() for m in modules}
    edges: list[DependencyEdge] = []
    for m in modules:
        src_span = Span(str(m.files[0]), 0, 0) if m.files else Span("", 0, 0)
        for imp in module_imports(m):
            target = m._grammar.resolve_module(imp.specifier, index)
            resolved = target is not None and target != m.id and target in module_ids
            edges.append(DependencyEdge(
                from_=m.id, to=target if resolved else None, kind=imp.kind,
                raw_specifier=imp.specifier, source=src_span, resolved=bool(resolved),
            ))
            if resolved:
                efferent[m.id].add(target)

    afferent: dict[ScopeId, set[ScopeId]] = {m.id: set() for m in modules}
    for src, tgts in efferent.items():
        for t in tgts:
            afferent[t].add(src)

    return ConcreteDependencyGraph(
        tuple(edges),
        {k: frozenset(v) for k, v in efferent.items()},
        {k: frozenset(v) for k, v in afferent.items()},
        label,
    )


def _iter_modules(component: Any):
    if component.KIND == ScopeKind.MODULE:
        yield component
        return
    for ch in component.children():
        yield from _iter_modules(ch)


def _module_names_for_path(fp: Path) -> list[str]:
    """All module-name spellings a grammar might emit for this path
    (ported from legacy build_module_index)."""
    names: list[str] = [fp.stem, fp.name]
    parts = fp.with_suffix("").parts
    if parts:
        for take in range(2, min(len(parts), 6) + 1):
            tail = parts[-take:]
            names.append(".".join(tail))
            names.append("/".join(tail))
    if fp.name == "__init__.py" and len(parts) >= 2:
        package_parts = parts[:-1]
        names.append(".".join(package_parts))
        names.append("/".join(package_parts))
        for take in range(1, min(len(package_parts), 5) + 1):
            tail = package_parts[-take:]
            names.append(".".join(tail))
            names.append("/".join(tail))
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out
