"""Structure — the structural-metric view over a region.

The structural twin of ``lexicon.Lexicon``: the view rules and tests consume.
Constructed ``Structure.over(region)`` (the view layer owns construction; the scope
entity grows no per-view methods). Aggregatable complexity is the primitive at a
Callable and the sum over descendant callables at a container.

Position-unique metrics answer at their home altitude (CK at a Class, Martin at a
Package, the cross-cutting ones at a Corpus) — the caller (a rule at that altitude, or
a test) supplies a region of the right kind. Methods that need cross-scope data read it from
``region.context`` (the corpus-global AnalysisContext).

Like the rest of ``metrics/structural``, it reads the region's duck-typed surface
(``_ast_node``/``_grammar``/``_node``/``_content``/``_iter_callables``/``_iter_classes``
+ the public scope accessors ``children``/``methods``/``modules``/``id``/``context``) —
the same surface ``clones`` uses — and imports no concrete scope class, so ``scope``
depends on this layer without a cycle and this layer stays a pure consumer of
``(region, context)``.
"""
from __future__ import annotations

from typing import Any

from ...identity import ScopeKind
from . import class_index, clones, cohesion, complexity, halstead, hotspots, literals
from .records import CKMetrics, Cohesion, PackageMetrics

# Zone boundaries on the instability and abstractness axes: the zone of pain is both below
# the first, the zone of uselessness both above the second.
_PAIN_BELOW = 0.3
_USELESS_ABOVE = 0.7


class Structure:
    """Structural metrics over one scope."""

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

    def _sum_over_callables(self, measure) -> int:
        return sum(measure(c._ast_node(), c._grammar) for c in self._leaves())

    def cyclomatic(self) -> int:
        return self._sum_over_callables(complexity.cyclomatic)

    def cognitive(self) -> int:
        return self._sum_over_callables(complexity.cognitive)

    def combinatorial(self) -> int:
        return self._sum_over_callables(complexity.combinatorial)

    def volume(self) -> float:
        """At a callable, its Halstead volume. Above one, the sum of its callables' volumes,
        which is a total and not itself a Halstead volume (vocabulary does not add)."""
        return float(sum(halstead.volume(c._ast_node(), c._grammar) for c in self._leaves()))

    # ---- Module measures: literals --------------------------------------
    def magic_floats(self):
        return literals.magic_floats(self._r)

    def repeated_strings(self, *, min_length: int = 5):
        return literals.repeated_strings(self._r, min_length=min_length)

    # ---- Class measures: Chidamber-Kemerer (dit/noc/cbo via the class index) --
    def ck(self) -> CKMetrics:
        cohesion = self.cohesion()
        caveats = class_index.caveats(self._r, self._class_index())
        if cohesion is None:
            caveats += (f"cohesion not measured: the {self._r._grammar.id} grammar does not say how "
                        f"instance members are accessed, so lcom4 is null, not 0",)
        return CKMetrics(nom=self.method_count(), dit=self.dit(), noc=self.noc(),
                         cbo=self.cbo(), cohesion=cohesion, caveats=caveats)

    def method_count(self) -> int:
        return len(self._r.methods())

    def dit(self) -> int:
        return self._class_measure(class_index.dit)

    def noc(self) -> int:
        return self._class_measure(class_index.noc)

    def cbo(self) -> int:
        return self._class_measure(class_index.cbo)

    def _class_measure(self, measure) -> int:
        return measure(self._r, self._class_index())

    def cohesion(self) -> Cohesion | None:
        """The class's method groups and detached methods, or ``None`` when the language's
        instance member access cannot be read from syntax."""
        r = self._r
        return cohesion.cohesion(r.methods(), r._grammar)

    def _class_index(self):
        idx = self._r.context.class_index if self._r.context else None
        if idx is None:
            raise NotImplementedError("CK metrics: class index not attached (build the corpus with scan_corpus)")
        return idx

    # ---- Module measures --------------------------------------------------
    def definition_count(self) -> int:
        return sum(1 for c in self._r.children()
                   if c.KIND in (ScopeKind.CALLABLE, ScopeKind.CLASS))

    def clone_clusters(self, *, min_leaf_nodes: int = 10):
        return clones.clone_clusters(list(self._r._iter_callables()), min_leaf_nodes=min_leaf_nodes)

    # ---- Package measures: Robert C. Martin (1994) ------------------------
    def _martin_raw(self) -> tuple[int, int, int, int]:
        ctx = self._r.context
        graph = ctx.dep_graph if ctx else None
        if graph is None:
            raise NotImplementedError("Package.martin: dependency graph not attached (build the corpus with scan_corpus)")
        modules = list(self._r.modules())
        ce = self._outside_packages(modules, ctx.module_pkg, graph.efferent_nodes)
        ca = self._outside_packages(modules, ctx.module_pkg, graph.afferent_nodes)
        na, nc = self._abstract_and_concrete()
        return len(ca), len(ce), na, nc

    def _outside_packages(self, modules, module_pkg, neighbours) -> set:
        """The other packages that own a module linked to ``modules`` by ``neighbours``."""
        found: set = set()
        for m in modules:
            for node in neighbours(m.id):
                pkg = module_pkg.get(node)
                if pkg is not None and pkg != self._r.id:
                    found.add(pkg)
        return found

    def _abstract_and_concrete(self) -> tuple[int, int]:
        """Counts of abstract and concrete classes; classes whose grammar cannot say are skipped."""
        verdicts = [cls._grammar.is_abstract_scope(cls._node, cls._content)
                    for cls in self._r._iter_classes()]
        return verdicts.count(True), verdicts.count(False)

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
        return (ce / (ca + ce)) < _PAIN_BELOW and (na / (na + nc)) < _PAIN_BELOW

    def in_zone_of_uselessness(self) -> bool:
        ca, ce, na, nc = self._martin_raw()
        if not (ca + ce) or not (na + nc):
            return False
        return (ce / (ca + ce)) > _USELESS_ABOVE and (na / (na + nc)) > _USELESS_ABOVE

    # ---- Corpus measures: analysis-wide -----------------------------------
    def duplication(self):
        return clones.clone_clusters(list(self._r._iter_callables()))

    def hotspots(self, *, since: str | None = None, last: int = hotspots.DEFAULT_LAST):
        return hotspots.hotspots(self._r, since=since, last=last)

    def dependency_cycles(self):
        ctx = self._r.context
        graph = ctx.dep_graph if ctx else None
        return graph.cycles() if graph is not None else []
