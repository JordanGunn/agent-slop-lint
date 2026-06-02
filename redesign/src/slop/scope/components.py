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

from .aggregate import Corpus as CorpusABC
from .aggregate import Package as PackageABC
from .aggregate import Realm as RealmABC
from .identity import CallableKind, ComponentId, ComponentKind, Extent
from .symbol import Callable as CallableABC
from .symbol import Class as ClassABC
from .symbol import Module as ModuleABC


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
        self._context = None  # AnalysisContext; carve hangs it on the Corpus root

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

    @property
    def context(self):
        """The corpus-global AnalysisContext, reached via the owner chain to the
        Corpus root (where carve hangs it). None until a scan attaches it."""
        node = self
        while node._owner is not None:
            node = node._owner
        return node._context

    # ---- projections --------------------------------------------------
    def lexicon(self):
        from .lexicon import build_lexicon
        return build_lexicon(self)

    def _ast_node(self) -> Any:
        """This component's own subtree as a ``slop.ast.Node``. The component
        holds the raw node from carving; every ported metric consumes the
        ``Node``, never the raw node — this is the single bridge from the stored
        node to the proxy."""
        from ..ast import Node
        path = self._files[0] if self._files else Path(".")
        return Node(self._node, self._content, path, self._grammar)

    # ---- descendant iteration (the region surface the metric views consume) --
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
    def bases(self):
        idx = self.context.class_index
        if idx is None:
            return ()
        return tuple(idx.by_name[b] for b in self._base_names if b in idx.by_name)
    def nested_classes(self): return tuple(c for c in self._children if c.KIND == ComponentKind.CLASS)
    def symbols(self): return self._children


class Module(_Base, ModuleABC):
    KIND = ComponentKind.MODULE

    def imports(self):
        from ..graph.imports import module_imports
        return module_imports(self)
    def symbols(self): return self._children


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

    def dependency_graph(self):
        """The corpus Module-level DependencyGraph (built during scan)."""
        return self.context.dep_graph

    @classmethod
    def scan(cls, root: Path, config: Any) -> "Corpus":
        from .carve import scan_corpus
        return scan_corpus(root, config)
