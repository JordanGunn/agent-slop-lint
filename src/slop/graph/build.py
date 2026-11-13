"""Concrete DependencyGraph — Module-level import edges over a Corpus.

Implements ``slop.graph.dependency.DependencyGraph``. Nodes are Module
ComponentIds; edges come from each Module's raw imports, resolved by its grammar
against the corpus's ``ModuleIndex`` and the importing file. Cycles via
Tarjan SCC. Neighbour-set accessors (beyond the ABC's count-returning
afferent/efferent) support Package-level contraction for Martin metrics.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ast.paradigm.base import ModuleIndex
from ..identity import ScopeId, Span, relative_path
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
                    ordered = sorted(comp, key=lambda c: (self._label[c], c.spans))
                    out.append(DependencyCycle(
                        members=tuple(self._label[c] for c in ordered), scopes=tuple(ordered)))

        for v in self._efferent:
            if v not in indexes:
                strongconnect(v)
        return out


def build(corpus: Any) -> ConcreteDependencyGraph:
    modules = list(corpus._iter_modules())
    label: dict[ScopeId, str] = {m.id: relative_path(m.id, corpus.root) or m.qualname for m in modules}
    index = _index(modules)
    edges = [edge for m in modules for edge in _edges(m, index, set(label))]
    efferent: dict[ScopeId, set[ScopeId]] = {m.id: set() for m in modules}
    for edge in edges:
        if edge.resolved:
            efferent[edge.from_].add(edge.to)

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


def _index(modules: list) -> ModuleIndex:
    """Every module by the spellings an import can use, and by its file."""
    index = ModuleIndex(by_name={}, by_path={})
    for m in modules:
        if not m.files:
            continue
        init_name = m._grammar.package_init_name() if m._grammar is not None else None
        for name in _module_names_for_path(m.files[0], init_name):
            index.by_name.setdefault(name, m.id)
        for key in ModuleIndex.keys(m.files[0]):
            index.by_path.setdefault(key, m.id)
    return index


def _edges(module: Any, index: ModuleIndex, module_ids: set[ScopeId]) -> list[DependencyEdge]:
    """One edge per corpus module each of ``module``'s imports loads; one unresolved edge for an
    import that loads none here (a self-import, or something outside the corpus)."""
    if not module.files:
        return []
    source = Span(str(module.files[0]), 0, 0)
    edges = []
    for imp in module_imports(module):
        targets = [t for t in module._grammar.resolve_import(imp, module.files[0], index)
                   if t != module.id and t in module_ids]
        edges += [DependencyEdge(from_=module.id, to=target, kind=imp.kind, raw_specifier=imp.specifier,
                                 source=source, resolved=target is not None)
                  for target in targets or [None]]
    return edges


def _module_names_for_path(fp: Path, init_name: str | None = None) -> list[str]:
    """All module-name spellings a grammar might emit for this path.

    ``init_name`` is the grammar's ``package_init_name()`` (Python ``__init__.py``,
    ``None`` elsewhere): a package-init module is also importable by its directory
    path, so it gets the extra parent-package spellings. Gating on the grammar fact
    instead of a hardcoded literal keeps non-Python languages out of this branch."""
    names: list[str] = [fp.stem, fp.name]
    parts = fp.with_suffix("").parts
    if parts:
        for take in range(2, min(len(parts), 6) + 1):
            tail = parts[-take:]
            names.append(".".join(tail))
            names.append("/".join(tail))
    if init_name is not None and fp.name == init_name and len(parts) >= 2:
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
