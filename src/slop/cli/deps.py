"""``slop deps``: the module dependency graph."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ..identity import relative_path
from ..scope.find import walk
from ..scope.identity import ScopeKind
from .render import add_output, header
from .resolve import add_root, add_scope, scan, select


def register(sub) -> None:
    p_deps = sub.add_parser("deps", help="print the module dependency graph")
    add_root(p_deps)
    add_scope(p_deps, "restrict to edges touching this module qualname", kind=False)
    p_deps.add_argument("--cycles", action="store_true", help="show only import cycles")
    add_output(p_deps)
    p_deps.set_defaults(run=lambda a: view(a.root, a.output, scope=a.scope, cycles_only=a.cycles))


def view(root: str | Path, output: str = "human", *, scope: str | None = None, cycles_only: bool = False) -> int:
    """Print the graph's edges and cycles, or with ``scope`` only the edges touching one module.

    Edges carry the ``resolved`` flag rather than forcing precision: an external or
    bare-specifier import shows as unresolved instead of a false edge."""
    corpus = scan(root)
    if corpus is None:
        return 2
    graph = corpus.context.dep_graph if corpus.context else None
    if graph is None:
        print("slop: error: no dependency graph available", file=sys.stderr)
        return 2
    base = str(corpus.root)

    def label(scope_id) -> str:
        # module qualnames are bare stems that collide across packages; the path is unambiguous
        return relative_path(scope_id, base) or scope_id.qualname

    edges = list(graph.edges())
    if scope is not None:
        module = select(corpus, scope)
        if module is None:
            return 2
        edges = _touching(edges, {module.qualname, label(module.id)}, label)
    cycles = graph.cycles()
    modules = sum(1 for c in walk(corpus) if c.id.kind is ScopeKind.MODULE)
    if output == "json":
        print(json.dumps({"modules": modules, "edges": [_edge(e, label) for e in edges],
                          "cycles": [list(c.members) for c in cycles]}, indent=2))
        return 0
    lines = [header("deps", scope or "corpus", f"{modules} modules · {len(edges)} edges · {len(cycles)} cycle(s)")]
    if not cycles_only:
        lines += _edges(graph, edges, label)
    lines += ["  cycle: " + " ↔ ".join(c.members) for c in cycles]
    print("\n".join(lines))
    return 0


def _edge(edge, label) -> dict:
    return {"from": label(edge.from_), "to": label(edge.to) if edge.to is not None else None,
            "kind": edge.kind, "resolved": edge.resolved, "raw_specifier": edge.raw_specifier}


def _touching(edges: list, keys: set[str], label) -> list:
    """The edges with an end that ``keys`` (a module's qualname and path) names."""
    def named(scope_id) -> bool:
        return scope_id is not None and bool({scope_id.qualname, label(scope_id)} & keys)
    return [e for e in edges if named(e.from_) or named(e.to)]


def _edges(graph, edges: list, label) -> list[str]:
    """One line per module: what it imports, and its efferent and afferent coupling."""
    imports: dict = {}
    for e in edges:
        if e.resolved and e.to is not None:
            imports.setdefault(e.from_, set()).add(label(e.to))
    lines = [f"  {label(node)}  → {', '.join(sorted(imports[node]))}   "
             f"(Ce {graph.efferent(node)} · Ca {graph.afferent(node)})"
             for node in sorted(imports, key=label)]
    unresolved = sum(1 for e in edges if not e.resolved)
    if unresolved:
        lines.append(f"  unresolved: {unresolved} edge(s) (external / bare specifiers)")
    return lines
