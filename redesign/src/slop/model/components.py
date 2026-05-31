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
        raise _todo("Lexicon", "projection pending (build step 4)")

    # ---- aggregatable complexity (container default = sum of leaves) --
    def _iter_callables(self) -> Iterator[Any]:
        for ch in self._children:
            if ch.KIND == ComponentKind.CALLABLE:
                yield ch
            yield from ch._iter_callables()

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

    def _cyclomatic(self) -> int: return complexity.cyclomatic(self._node, self._content, self._grammar)
    def _cognitive(self) -> int: return complexity.cognitive(self._node, self._content, self._grammar)
    def _combinatorial(self) -> int: return complexity.combinatorial(self._node, self._grammar)
    def _volume(self) -> float: return halstead.volume(self._node, self._content, self._grammar)
    def _sloc(self) -> int: return halstead.sloc(self._node, self._content)

    # CallableMeasures (non-aggregatable)
    def halstead(self): return halstead.profile(self._node, self._content, self._grammar)
    def halstead_density(self) -> float: return halstead.profile(self._node, self._content, self._grammar).difficulty
    def magic_literals(self): return callable_measures.magic_literals(self._node, self._content, self._grammar)
    def mutated_parameters(self): return callable_measures.mutated_parameters(self._node, self._content, self._grammar)
    def sentinel_parameters(self): return callable_measures.sentinel_parameters(self._node, self._content, self._grammar)


class Class(_Base, ClassABC):
    KIND = ComponentKind.CLASS

    def __init__(self, *, is_abstract: bool, bases: tuple[str, ...], properties: tuple[str, ...], **kw: Any) -> None:
        super().__init__(**kw)
        self._is_abstract = is_abstract
        self._base_names = bases
        self._properties = properties

    @property
    def is_abstract(self) -> bool: return self._is_abstract
    def methods(self): return tuple(c for c in self._children if c.KIND == ComponentKind.CALLABLE)
    def properties(self): return self._properties
    def bases(self): raise _todo("Class.bases", "resolved-superclass linking pending")
    def nested_classes(self): return tuple(c for c in self._children if c.KIND == ComponentKind.CLASS)
    def symbols(self): return self._children

    # ClassMeasures (CK)
    def ck(self): raise _todo("Class.ck", "CK walkers pending")
    def method_count(self) -> int: return len(self.methods())
    def dit(self): raise _todo("Class.dit", "inheritance linking pending")
    def noc(self): raise _todo("Class.noc", "inheritance linking pending")
    def cbo(self): raise _todo("Class.cbo", "coupling walker pending")
    def lcom(self): return None  # not in legacy; future


class Module(_Base, ModuleABC):
    KIND = ComponentKind.MODULE

    def imports(self): raise _todo("Module.imports", "import extraction pending")
    def symbols(self): return self._children

    # ModuleMeasures
    def definition_count(self) -> int:
        return sum(1 for c in self._children if c.KIND in (ComponentKind.CALLABLE, ComponentKind.CLASS))
    def escape_hatch_density(self) -> float:
        from .annotations import escape_hatch_density as _ehd
        return _ehd(self._node, self._content, self._grammar)
    def redundant_siblings(self): raise _todo("Module.redundant_siblings", "callee-overlap pending")
    def call_islands(self): raise _todo("Module.call_islands", "intra-module call topology pending")
    def clone_clusters(self): raise _todo("Module.clone_clusters", "clone fingerprinting pending")


# ============================ aggregate containers ========================

class Package(_Base, PackageABC):
    KIND = ComponentKind.PACKAGE

    def __init__(self, *, path: Path, **kw: Any) -> None:
        super().__init__(**kw)
        self._path = path

    @property
    def path(self) -> Path: return self._path
    def packages(self): return tuple(c for c in self._children if c.KIND == ComponentKind.PACKAGE)
    def modules(self): return tuple(c for c in self._children if c.KIND == ComponentKind.MODULE)

    # PackageMeasures — graph-dependent, out of scope
    def martin_metrics(self): raise _todo("Package.martin_metrics", "needs DependencyGraph (out of scope)")
    def in_zone_of_pain(self): raise _todo("Package.in_zone_of_pain", "needs DependencyGraph (out of scope)")
    def in_zone_of_uselessness(self): raise _todo("Package.in_zone_of_uselessness", "needs DependencyGraph (out of scope)")
    def is_runt(self): raise _todo("Package.is_runt", "pending")


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

    @property
    def root(self) -> Path: return self._root
    @property
    def config(self): return self._config
    def realms(self): return tuple(c for c in self._children if c.KIND == ComponentKind.REALM)

    @classmethod
    def scan(cls, root: Path, config: Any) -> "Corpus":
        from .carve import scan_corpus
        return scan_corpus(root, config)

    # CorpusMeasures — graph-dependent / cross-cutting
    def orphans(self): raise _todo("Corpus.orphans", "cross-file reference search pending")
    def duplication(self): raise _todo("Corpus.duplication", "clone fingerprinting pending")
    def hotspots(self): raise _todo("Corpus.hotspots", "git-churn join pending")
    def dependency_cycles(self): raise _todo("Corpus.dependency_cycles", "needs DependencyGraph (out of scope)")
