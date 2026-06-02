"""Concrete component classes implementing the pure interfaces in
``slop.component``. The interfaces are untouched; these are their realisation.

``_Base`` provides the universal scope surface (id/name/owner/extent/files/
children/ast) and the container-style aggregatable complexity (sum over
descendant callables). Each concrete kind implements its kind-specific surface
and measures. Metrics not yet ported, and graph-dependent measures, raise
``NotImplementedError`` with a pointer — they are still concrete (instantiable),
filled in incrementally per the goal.
"""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from ..component.aggregate import Corpus as CorpusABC
from ..component.aggregate import Package as PackageABC
from ..component.aggregate import Realm as RealmABC
from ..component.identity import CallableKind, ComponentId, ComponentKind, Extent
from ..component.symbol import Callable as CallableABC
from ..component.symbol import Class as ClassABC
from ..component.symbol import Module as ModuleABC
from . import callable_measures, complexity, halstead
from .ast import AST, Root


def _todo(what: str, why: str) -> NotImplementedError:
    return NotImplementedError(f"{what}: {why}")


class _Base:
    """Universal scope surface + container complexity aggregation. Mixed in
    before the kind ABC so its concrete methods satisfy the abstract ones."""

    def __init__(
        self,
        *,
        id: ComponentId,
        name: str,
        owner: Any | None,
        extent: Extent,
        files: tuple[Path, ...],
        children: Sequence[Any] = (),
        node: Any = None,
        content: bytes = b"",
        grammar: type | None = None,
    ) -> None:
        self._id = id
        self._name = name
        self._owner = owner
        self._extent = extent
        self._files = files
        self._children = tuple(children)
        self._node = node
        self._content = content
        self._grammar = grammar

    # ---- universal identity / location -------------------------------
    @property
    def id(self) -> ComponentId: return self._id
    @property
    def name(self) -> str: return self._name
    @property
    def owner(self): return self._owner
    @property
    def extent(self) -> Extent: return self._extent
    @property
    def files(self) -> tuple[Path, ...]: return self._files
    def children(self): return self._children

    # ---- projections --------------------------------------------------
    def ast(self) -> AST:
        if self._node is not None:
            path = self._files[0] if self._files else Path(".")
            return AST((Root(node=self._node, content=self._content, path=path),))
        roots: list[Root] = []
        for ch in self._children:
            roots.extend(ch.ast().roots)
        return AST(tuple(roots))

    def lexicon(self):
        from .lexicon import build_lexicon
        return build_lexicon(self)

    def _ast_node(self) -> Any:
        """Wrap this component's own tree-sitter node in the AST proxy. The
        component holds the raw node from carving; ported metrics consume the
        ``Node``, never the raw node. Transitional — once carving emits the
        proxy directly, the stored raw node and this helper dissolve."""
        from ..ast import Node
        path = self._files[0] if self._files else Path(".")
        return Node(self._node, self._content, path, self._grammar)

    # ---- aggregatable complexity (container default = sum of leaves) --
    def _iter_callables(self) -> Iterator[Any]:
        for ch in self._children:
            if ch.KIND == ComponentKind.CALLABLE:
                yield ch
            yield from ch._iter_callables()

    def _iter_classes(self) -> Iterator[Any]:
        for ch in self._children:
            if ch.KIND == ComponentKind.CLASS:
                yield ch
            yield from ch._iter_classes()

    def _sum(self, prim: str) -> int:
        return sum(getattr(cl, prim)() for cl in self._iter_callables())

    def cyclomatic(self) -> int: return self._sum("_cyclomatic")
    def cognitive(self) -> int: return self._sum("_cognitive")
    def combinatorial(self) -> int: return self._sum("_combinatorial")
    def volume(self) -> float: return float(self._sum("_volume"))
    def sloc(self) -> int: return self._sum("_sloc")


# ============================ symbol containers ============================

class Callable(_Base, CallableABC):
    KIND = ComponentKind.CALLABLE

    def __init__(self, *, kind: CallableKind, parameters: tuple[str, ...], **kw: Any) -> None:
        super().__init__(**kw)
        self._kind = kind
        self._parameters = parameters

    @property
    def kind(self) -> CallableKind: return self._kind
    def parameters(self): return self._parameters
    def locals(self): raise _todo("Callable.locals", "pending")
    def nested(self): return tuple(c for c in self._children if c.KIND == ComponentKind.CALLABLE)
    def symbols(self): return self._children

    # complexity: a Callable reports its own primitive (override the sum)
    def cyclomatic(self) -> int: return self._cyclomatic()
    def cognitive(self) -> int: return self._cognitive()
    def combinatorial(self) -> int: return self._combinatorial()
    def volume(self) -> float: return float(self._volume())
    def sloc(self) -> int: return self._sloc()

    def _cyclomatic(self) -> int: return complexity.cyclomatic(self._ast_node(), self._grammar)
    def _cognitive(self) -> int: return complexity.cognitive(self._ast_node(), self._grammar)
    def _combinatorial(self) -> int: return complexity.combinatorial(self._ast_node(), self._grammar)
    def _volume(self) -> float: return halstead.volume(self._ast_node(), self._grammar)
    def _sloc(self) -> int: return halstead.sloc(self._ast_node())

    # CallableMeasures (non-aggregatable)
    def halstead(self): return halstead.profile(self._ast_node(), self._grammar)
    def halstead_density(self) -> float: return halstead.profile(self._ast_node(), self._grammar).difficulty
    def magic_literals(self): return callable_measures.magic_literals(self._ast_node(), self._grammar)
    def mutated_parameters(self): return callable_measures.mutated_parameters(self._node, self._content, self._grammar)
    def sentinel_parameters(self): return callable_measures.sentinel_parameters(self._node, self._content, self._grammar)


class Class(_Base, ClassABC):
    KIND = ComponentKind.CLASS

    def __init__(self, *, is_abstract: bool, bases: tuple[str, ...], properties: tuple[str, ...], **kw: Any) -> None:
        super().__init__(**kw)
        self._is_abstract = is_abstract
        self._base_names = bases
        self._properties = properties
        self._class_index: Any = None  # attached post-carve (corpus-wide)

    @property
    def is_abstract(self) -> bool: return self._is_abstract
    def methods(self): return tuple(c for c in self._children if c.KIND == ComponentKind.CALLABLE)
    def properties(self): return self._properties
    def bases(self):
        idx = self._class_index
        if idx is None:
            return ()
        return tuple(idx.by_name[b] for b in self._base_names if b in idx.by_name)
    def nested_classes(self): return tuple(c for c in self._children if c.KIND == ComponentKind.CLASS)
    def symbols(self): return self._children

    # ClassMeasures (CK) — dit/noc/cbo use the corpus-wide class index
    def ck(self):
        from ..component.metrics import CKMetrics
        return CKMetrics(nom=self.method_count(), dit=self.dit(), noc=self.noc(),
                         cbo=self.cbo(), lcom=self.lcom())
    def method_count(self) -> int: return len(self.methods())
    def dit(self) -> int:
        from . import class_index
        return class_index.dit(self, self._require_index())
    def noc(self) -> int:
        from . import class_index
        return class_index.noc(self, self._require_index())
    def cbo(self) -> int:
        from . import class_index
        return class_index.cbo(self, self._require_index())
    def lcom(self): return None  # not in legacy; future

    def _require_index(self):
        if self._class_index is None:
            raise _todo("CK metrics", "class index not attached (scan via Corpus.scan)")
        return self._class_index


class Module(_Base, ModuleABC):
    KIND = ComponentKind.MODULE

    def imports(self):
        from .imports import module_imports
        return module_imports(self)
    def symbols(self): return self._children

    # ModuleMeasures
    def definition_count(self) -> int:
        return sum(1 for c in self._children if c.KIND in (ComponentKind.CALLABLE, ComponentKind.CLASS))
    def escape_hatch_density(self) -> float:
        from .annotations import escape_hatch_density as _ehd
        return _ehd(self._ast_node(), self._grammar)
    def redundant_siblings(self):
        from .relational import redundant_siblings
        return redundant_siblings(self)
    def call_islands(self):
        from .relational import call_islands
        return call_islands(self)
    def clone_clusters(self):
        from .relational import clone_clusters
        return clone_clusters(list(self._iter_callables()))


# ============================ aggregate containers ========================

class Package(_Base, PackageABC):
    KIND = ComponentKind.PACKAGE

    def __init__(self, *, path: Path, **kw: Any) -> None:
        super().__init__(**kw)
        self._path = path
        self._dep_graph: Any = None        # attached post-carve
        self._module_pkg: dict = {}        # module id -> package id

    @property
    def path(self) -> Path: return self._path
    def packages(self): return tuple(c for c in self._children if c.KIND == ComponentKind.PACKAGE)
    def modules(self): return tuple(c for c in self._children if c.KIND == ComponentKind.MODULE)

    # PackageMeasures (Martin 1994) — uses the corpus DependencyGraph contracted
    # to package granularity + abstractness from the grammar's classification.
    def _martin_raw(self) -> tuple[int, int, int, int]:
        if self._dep_graph is None:
            raise _todo("Package.martin", "dependency graph not attached (scan via Corpus.scan)")
        ce: set = set(); ca: set = set()
        for m in self.modules():
            for t in self._dep_graph.efferent_nodes(m.id):
                p = self._module_pkg.get(t)
                if p is not None and p != self.id:
                    ce.add(p)
            for s in self._dep_graph.afferent_nodes(m.id):
                p = self._module_pkg.get(s)
                if p is not None and p != self.id:
                    ca.add(p)
        na = nc = 0
        for cls in self._iter_classes():
            c = cls._grammar.is_abstract_scope(cls._node, cls._content)
            if c is True:
                na += 1
            elif c is False:
                nc += 1
        return len(ca), len(ce), na, nc

    def martin_metrics(self):
        from ..component.metrics import PackageMetrics
        ca, ce, na, nc = self._martin_raw()
        i = ce / (ca + ce) if (ca + ce) else 0.0
        a = na / (na + nc) if (na + nc) else 0.0
        return PackageMetrics(afferent=ca, efferent=ce, instability=i, abstractness=a,
                              distance=abs(a + i - 1.0))

    def in_zone_of_pain(self) -> bool:
        ca, ce, na, nc = self._martin_raw()
        if not (ca + ce) or not (na + nc):
            return False  # undefined — not classifiable
        return (ce / (ca + ce)) < 0.3 and (na / (na + nc)) < 0.3

    def in_zone_of_uselessness(self) -> bool:
        ca, ce, na, nc = self._martin_raw()
        if not (ca + ce) or not (na + nc):
            return False
        return (ce / (ca + ce)) > 0.7 and (na / (na + nc)) > 0.7
    def is_runt(self) -> bool:
        """A package whose boundary does not earn its weight: <=1 module and no
        top-level definitions (a trivial single-/empty-module package)."""
        mods = self.modules()
        return len(mods) <= 1 and sum(m.definition_count() for m in mods) == 0


class Realm(_Base, RealmABC):
    KIND = ComponentKind.REALM

    def __init__(self, *, root: Path, grammar: type, language: str, **kw: Any) -> None:
        super().__init__(**kw)
        self._root = root
        self._grammar = grammar
        self._language = language

    @property
    def root(self) -> Path: return self._root
    @property
    def grammar(self) -> type: return self._grammar
    @property
    def language(self) -> str: return self._language
    def packages(self): return tuple(c for c in self._children if c.KIND == ComponentKind.PACKAGE)


class Corpus(_Base, CorpusABC):
    KIND = ComponentKind.CORPUS

    def __init__(self, *, root: Path, config: Any, **kw: Any) -> None:
        super().__init__(**kw)
        self._root = root
        self._config = config
        self._dep_graph: Any = None  # attached post-carve

    @property
    def root(self) -> Path: return self._root
    @property
    def config(self): return self._config
    def realms(self): return tuple(c for c in self._children if c.KIND == ComponentKind.REALM)

    def dependency_graph(self):
        """The corpus Module-level DependencyGraph (built during scan)."""
        return self._dep_graph

    @classmethod
    def scan(cls, root: Path, config: Any) -> "Corpus":
        from .carve import scan_corpus
        return scan_corpus(root, config)

    # CorpusMeasures — graph-dependent / cross-cutting
    def orphans(self):
        from .orphans import orphans
        return orphans(self)
    def duplication(self):
        from .relational import clone_clusters
        return clone_clusters(list(self._iter_callables()))
    def hotspots(self):
        from .hotspots import hotspots
        return hotspots(self)
    def dependency_cycles(self):
        return self._dep_graph.cycles() if self._dep_graph is not None else []
