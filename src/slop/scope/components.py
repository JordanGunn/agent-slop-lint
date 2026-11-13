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

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..ast.accessor import is_accessor
from . import aggregate, symbol
from .descendants import Descendants
from .identity import CallableKind, ScopeId, ScopeKind, Extent


class _Base(Descendants):
    """Universal scope surface: identity, location and children, with the bridges to the
    lexicon and the AST. Mixed in before the kind ABC so its concrete methods satisfy the
    abstract ones."""

    def __init__(
        self,
        *,
        id: ScopeId,
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
        self._bindings: dict | None = None  # a Module's name bindings, computed on first use

    # ---- universal identity / location -------------------------------
    @property
    def id(self) -> ScopeId: return self._id
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
    def line(self) -> int:
        """1-based start line of this component in its file, or 0 if the source
        position is unknown. The canonical locus for findings about this scope."""
        node = self._node
        if node is not None and getattr(node, "start_point", None) is not None:
            return node.start_point[0] + 1
        return 0

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
        from .lexicon import build_declared_lexicon
        return build_declared_lexicon(self)

    def bindings(self) -> dict:
        """What each name in this component's file refers to, keyed by start byte
        (``slop.ast.binding``): computed once per file, on its Module."""
        module = self
        while module.id.kind is not ScopeKind.MODULE and module._owner is not None:
            module = module._owner
        if module._bindings is None:
            from ..ast.binding import bind
            module._bindings = bind(module._node, module._content, module._grammar) if module._node is not None else {}
        return module._bindings

    def _ast_node(self) -> Any:
        """This component's own subtree as a ``slop.ast.Node``. The component
        holds the raw node from carving; every ported metric consumes the
        ``Node``, never the raw node — this is the single bridge from the stored
        node to the proxy."""
        from ..ast import Node
        path = self._files[0] if self._files else Path(".")
        return Node(self._node, self._content, path, self._grammar)


# ============================ symbol containers ============================

class Callable(_Base, symbol.Callable):
    KIND = ScopeKind.CALLABLE

    def __init__(self, *, kind: CallableKind, parameters: tuple[str, ...], **kw: Any) -> None:
        super().__init__(**kw)
        self._kind = kind
        self._parameters = parameters
        self._kind_settled = False

    @property
    def kind(self) -> CallableKind:
        """The callable's kind. Carving knows lambdas, methods and functions from syntax alone. A
        method is then a constructor when its grammar names it one (``__init__``, ``constructor``)
        or it is named like its class (Java, C#, C++), and otherwise an accessor when it is a
        getter or setter (``slop.ast.accessor``). Both are decided on first read: a method's class
        is known only once carving is done, and the accessor test needs the file's bindings."""
        if self._kind is CallableKind.METHOD and not self._kind_settled:
            self._kind_settled = True
            if self.name in self._grammar.constructor_names() or (
                    self._owner is not None and self.name == self._owner.name):
                self._kind = CallableKind.CONSTRUCTOR
            elif is_accessor(self._node, self._content, self._grammar, self.bindings()):
                self._kind = CallableKind.ACCESSOR
        return self._kind

    def parameters(self): return self._parameters
    def nested(self): return self._children_of(ScopeKind.CALLABLE)
    def symbols(self): return self._children


class Class(_Base, symbol.Class):
    KIND = ScopeKind.CLASS

    def __init__(self, *, is_abstract: bool, bases: tuple[str, ...], **kw: Any) -> None:
        super().__init__(**kw)
        self._is_abstract = is_abstract
        self._base_names = bases
        self._properties: tuple[str, ...] | None = None

    @property
    def is_abstract(self) -> bool: return self._is_abstract
    def methods(self): return self._children_of(ScopeKind.CALLABLE)
    def properties(self) -> tuple[str, ...]:
        """The fields this class declares (``slop.scope.properties``), read on first use."""
        if self._properties is None:
            from .properties import class_properties
            self._properties = class_properties(self)
        return self._properties
    def bases(self):
        idx = self.context.class_index
        if idx is None:
            return ()
        return idx.parents.get(self.id, ())
    def nested_classes(self): return self._children_of(ScopeKind.CLASS)
    def symbols(self): return self._children


class Module(_Base, symbol.Module):
    KIND = ScopeKind.MODULE

    def imports(self):
        from ..graph.imports import module_imports
        return module_imports(self)
    def symbols(self): return self._children


# ============================ aggregate containers ========================

class Package(_Base, aggregate.Package):
    KIND = ScopeKind.PACKAGE

    def __init__(self, *, path: Path, **kw: Any) -> None:
        super().__init__(**kw)
        self._path = path

    @property
    def path(self) -> Path: return self._path
    def modules(self): return self._children_of(ScopeKind.MODULE)


class Realm(_Base, aggregate.Realm):
    KIND = ScopeKind.REALM

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
    def packages(self): return self._children_of(ScopeKind.PACKAGE)


class Corpus(_Base, aggregate.Corpus):
    KIND = ScopeKind.CORPUS

    def __init__(self, *, root: Path, config: Any, **kw: Any) -> None:
        super().__init__(**kw)
        self._root = root
        self._config = config

    @property
    def root(self) -> Path: return self._root
    @property
    def config(self): return self._config
    def realms(self): return self._children_of(ScopeKind.REALM)
