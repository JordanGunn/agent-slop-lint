"""Building the dependency graph: every module's imports, resolved by its grammar against the
corpus's module index and the importing file, become the edges of a ``DependencyGraph``."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ast.paradigm.base import ModuleIndex
from ..identity import ScopeId, Span, relative_path
from .dependency import DependencyEdge, DependencyGraph
from .imports import module_imports


def build(corpus: Any) -> DependencyGraph:
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

    return DependencyGraph(
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
