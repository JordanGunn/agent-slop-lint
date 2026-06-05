"""Structure — the structural-metric view over a region.

The structural twin of ``lexicon.Lexicon``: the view rules and tests consume.
Constructed ``Structure.over(region)`` (the view layer owns construction; the scope
entity grows no per-view methods). Aggregatable complexity is the primitive at a
Callable and the sum over descendant callables at a container.

Position-unique metrics answer at their home altitude (CK at a Class, Martin at a
Package, the cross-cutting ones at a Corpus) — the caller (a rule at that altitude, or
a test) supplies a region of the right kind, exactly as the legacy altitude-typed
measure mixins required. Methods that need cross-scope data read it from
``region.context`` (the corpus-global AnalysisContext).

Like the rest of ``metrics/structural``, it reads the region's duck-typed surface
(``_ast_node``/``_grammar``/``_node``/``_content``/``_iter_callables``/``_iter_classes``
+ the public scope accessors ``children``/``methods``/``modules``/``id``/``context``) —
the same surface ``relational`` uses — and imports no concrete scope class, so ``scope``
depends on this layer without a cycle and this layer stays a pure consumer of
``(region, context)``.
"""
from __future__ import annotations

from typing import Any

from ...identity import ScopeKind
from . import callable_measures, class_index, complexity, halstead
from .annotations import (
    escape_hatch_counts as _escape_hatch_counts,
    escape_hatch_density as _escape_hatch_density,
)
from .hotspots import _DEFAULT_WINDOW as _HOTSPOT_WINDOW, hotspots as _hotspots
from .orphans import orphans as _orphans
from .records import CKMetrics, PackageMetrics
from .runts import is_runt as _is_runt
from .relational import (
    call_islands as _call_islands,
    clone_clusters as _clone_clusters,
    redundant_siblings as _redundant_siblings,
)


def _todo(what: str, why: str) -> NotImplementedError:
    return NotImplementedError(f"{what}: {why}")


class Structure:
    """Structural metrics over one region (a scope, or — later — a selection)."""

    def __init__(self, region: Any) -> None:
        self._r = region

    @classmethod
    def over(cls, region: Any) -> "Structure":
        return cls(region)

    # ---- aggregatable complexity: own primitive at a Callable, summed over
    #      descendant callables at a container (each leaf counted once) --------
    def _leaves(self) -> list[Any]:
        r = self._r
        return [r] if r.KIND == ScopeKind.CALLABLE else list(r._iter_callables())

    def cyclomatic(self) -> int:
        return sum(complexity.cyclomatic(c._ast_node(), c._grammar) for c in self._leaves())

    def cognitive(self) -> int:
        return sum(complexity.cognitive(c._ast_node(), c._grammar) for c in self._leaves())

    def combinatorial(self) -> int:
        return sum(complexity.combinatorial(c._ast_node(), c._grammar) for c in self._leaves())

    def volume(self) -> float:
        return float(sum(halstead.volume(c._ast_node(), c._grammar) for c in self._leaves()))

    def sloc(self) -> int:
        return sum(halstead.sloc(c._ast_node()) for c in self._leaves())

    # ---- Callable measures (non-aggregatable) -----------------------------
    def halstead(self):
        r = self._r
        return halstead.profile(r._ast_node(), r._grammar)

    def halstead_density(self) -> float:
        r = self._r
        return halstead.profile(r._ast_node(), r._grammar).difficulty

    def magic_literals(self):
        r = self._r
        return callable_measures.magic_literals(r._ast_node(), r._grammar)

    def mutated_parameters(self):
        r = self._r
        return callable_measures.mutated_parameters(r._node, r._content, r._grammar)

    def sentinel_parameters(self):
        r = self._r
        return callable_measures.sentinel_parameters(r._node, r._content, r._grammar)

    # ---- Class measures: Chidamber-Kemerer (dit/noc/cbo via the class index) --
    def ck(self) -> CKMetrics:
        return CKMetrics(nom=self.method_count(), dit=self.dit(), noc=self.noc(),
                         cbo=self.cbo(), lcom=self.lcom())

    def method_count(self) -> int:
        return len(self._r.methods())

    def dit(self) -> int:
        return class_index.dit(self._r, self._class_index())

    def noc(self) -> int:
        return class_index.noc(self._r, self._class_index())

    def cbo(self) -> int:
        return class_index.cbo(self._r, self._class_index())

    def lcom(self):
        return None  # not in legacy; future

    def _class_index(self):
        idx = self._r.context.class_index if self._r.context else None
        if idx is None:
            raise _todo("CK metrics", "class index not attached (scan via Corpus.scan)")
        return idx

    # ---- Module measures --------------------------------------------------
    def definition_count(self) -> int:
        return sum(1 for c in self._r.children()
                   if c.KIND in (ScopeKind.CALLABLE, ScopeKind.CLASS))

    def escape_hatch_density(self) -> float:
        r = self._r
        return _escape_hatch_density(r._ast_node(), r._grammar)

    def escape_hatch_counts(self) -> tuple[int, int]:
        """``(escape-hatch annotations, total annotations)`` — the raw counts the
        escape-hatches rule gates on (density plus the min-annotations floor)."""
        r = self._r
        return _escape_hatch_counts(r._ast_node(), r._grammar)

    def redundant_siblings(self, *, min_shared: int = 3, min_score: float = 0.5,
                           exclude: frozenset[str] = frozenset()):
        return _redundant_siblings(self._r, min_shared=min_shared, min_score=min_score,
                                   exclude=exclude)

    def call_islands(self):
        """Disjoint components of the module's intra-file call graph."""
        return _call_islands(self._r)

    def clone_clusters(self, *, min_leaf_nodes: int = 10):
        return _clone_clusters(list(self._r._iter_callables()), min_leaf_nodes=min_leaf_nodes)

    # ---- Package measures: Robert C. Martin (1994) ------------------------
    def _martin_raw(self) -> tuple[int, int, int, int]:
        ctx = self._r.context
        graph = ctx.dep_graph if ctx else None
        if graph is None:
            raise _todo("Package.martin", "dependency graph not attached (scan via Corpus.scan)")
        module_pkg = ctx.module_pkg
        ce: set = set()
        ca: set = set()
        for m in self._r.modules():
            for t in graph.efferent_nodes(m.id):
                p = module_pkg.get(t)
                if p is not None and p != self._r.id:
                    ce.add(p)
            for s in graph.afferent_nodes(m.id):
                p = module_pkg.get(s)
                if p is not None and p != self._r.id:
                    ca.add(p)
        na = nc = 0
        for cls in self._r._iter_classes():
            c = cls._grammar.is_abstract_scope(cls._node, cls._content)
            if c is True:
                na += 1
            elif c is False:
                nc += 1
        return len(ca), len(ce), na, nc

    def martin_metrics(self) -> PackageMetrics:
        ca, ce, na, nc = self._martin_raw()
        i = ce / (ca + ce) if (ca + ce) else 0.0
        a = na / (na + nc) if (na + nc) else 0.0
        return PackageMetrics(afferent=ca, efferent=ce, instability=i, abstractness=a,
                              distance=abs(a + i - 1.0))

    def in_zone_of_pain(self) -> bool:
        ca, ce, na, nc = self._martin_raw()
        if not (ca + ce) or not (na + nc):
            return False
        return (ce / (ca + ce)) < 0.3 and (na / (na + nc)) < 0.3

    def in_zone_of_uselessness(self) -> bool:
        ca, ce, na, nc = self._martin_raw()
        if not (ca + ce) or not (na + nc):
            return False
        return (ce / (ca + ce)) > 0.7 and (na / (na + nc)) > 0.7

    def is_runt(self) -> bool:
        return _is_runt(self._r)

    # ---- Corpus measures: analysis-wide -----------------------------------
    def orphans(self):
        return _orphans(self._r)

    def duplication(self):
        return _clone_clusters(list(self._r._iter_callables()))

    def hotspots(self, *, since: str = _HOTSPOT_WINDOW):
        return _hotspots(self._r, since=since)

    def dependency_cycles(self):
        ctx = self._r.context
        graph = ctx.dep_graph if ctx else None
        return graph.cycles() if graph is not None else []
