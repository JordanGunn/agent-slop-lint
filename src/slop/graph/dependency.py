"""The dependency graph: modules, the imports between them, and its cycles."""
from __future__ import annotations

from dataclasses import dataclass

from ..identity import ScopeId, Span


@dataclass(frozen=True)
class DependencyCycle:
    """A strongly-connected component in the import graph (Tarjan SCC, >1 node).

    ``scopes`` are the modules' identities and ``members`` their labels (root-relative
    path), in the same order: two modules with one name (``a/x.py``, ``b/x.py``) stay two
    modules."""

    members: tuple[str, ...]
    scopes: tuple[ScopeId, ...]


@dataclass(frozen=True)
class DependencyEdge:
    """A directed dependency between two scopes, evidence preserved.

    ``to`` may be unresolved (an external dependency or bare specifier string),
    so the edge records ``resolved`` and the ``raw_specifier`` rather than
    forcing false precision.
    """

    from_: ScopeId
    to: ScopeId | None
    kind: str               # import | include | require | use | build | reference
    raw_specifier: str
    source: Span
    resolved: bool


class DependencyGraph:
    """Which modules import which. Nodes are module ``ScopeId``s; ``edges`` keep the import as
    written and whether it resolved. ``afferent``/``efferent`` count a module's dependents and
    dependencies (Martin's Ca and Ce), the ``*_nodes`` forms list them so a package's counts can
    be contracted from its modules', and ``cycles`` are the import cycles (Tarjan's strongly
    connected components with more than one module)."""

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
        # Tarjan SCC over the efferent map; strongly connected components with >1 node are cycles.
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


