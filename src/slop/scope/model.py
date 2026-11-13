"""The scope's model: the tree slop carves the sources into.

    Corpus -> Realm -> Package -> Module -> Class -> Callable

A scope is a named region of source with a stable identity (``ScopeId``), the source it owns
(its ``extent``), the files it spans, an owner (none for the corpus) and children. ``Scope``
holds what every kind shares; each kind adds what only it has. Measurements are not methods
here: ``Structure.over(scope)`` (``slop.metrics.structural``) reads a scope's nodes, and the
rules read the measurements.
"""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, ClassVar

from ..ast.accessor import is_accessor
from .identity import CallableKind, Extent, ScopeId, ScopeKind


class Scope:
    """What every kind of scope has: identity, location, owner and children, the bridges to its
    syntax (``_ast_node``), its name bindings and its lexicon, and iteration over descendants
    by kind."""

    #: The kind of scope this class models, a constant so dispatch never inspects the object.
    KIND: ClassVar[ScopeKind]

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
        self._context = None  # the AnalysisContext; carving sets it on the corpus
        self._bindings: dict | None = None  # a module's name bindings, computed on first use

    @property
    def id(self) -> ScopeId:
        """Stable, hashable identity; two scopes with equal ids are the same scope."""
        return self._id

    @property
    def name(self) -> str:
        """The local name, the last segment of ``qualname``."""
        return self._name

    @property
    def qualname(self) -> str:
        """The dotted ownership path (``pkg.mod.Class.method``)."""
        return self._id.qualname

    @property
    def owner(self) -> Scope | None:
        """The scope this one belongs to; None for the corpus."""
        return self._owner

    @property
    def extent(self) -> Extent:
        """The source this scope owns, as byte spans."""
        return self._extent

    @property
    def files(self) -> tuple[Path, ...]:
        """The distinct files this scope spans. A Python module has one; a Go module has every
        file of its package directory; a container has the union of its descendants'."""
        return self._files

    def children(self) -> tuple[Any, ...]:
        """The scopes directly inside this one."""
        return self._children

    @property
    def line(self) -> int:
        """1-based line where this scope's definition starts, or 0 when it has none."""
        node = self._node
        if node is not None and getattr(node, "start_point", None) is not None:
            return node.start_point[0] + 1
        return 0

    @property
    def context(self):
        """The corpus-wide AnalysisContext, held by the corpus at the top of the owner chain;
        None until a scan sets it."""
        scope = self
        while scope._owner is not None:
            scope = scope._owner
        return scope._context

    def lexicon(self):
        """The words of the names declared in this scope (``slop.scope.lexicon``)."""
        from .lexicon import build_declared_lexicon
        return build_declared_lexicon(self)

    def bindings(self) -> dict:
        """What each name in this scope's file refers to, keyed by start byte
        (``slop.ast.binding``): computed once per file, on its module."""
        module = self
        while module.id.kind is not ScopeKind.MODULE and module._owner is not None:
            module = module._owner
        if module._bindings is None:
            from ..ast.binding import bind
            module._bindings = bind(module._node, module._content, module._grammar) if module._node is not None else {}
        return module._bindings

    def _ast_node(self) -> Any:
        """This scope's subtree as a ``slop.ast.Node``, the one bridge from the raw node carving
        stored to the proxy every measure reads."""
        from ..ast import Node
        path = self._files[0] if self._files else Path(".")
        return Node(self._node, self._content, path, self._grammar)

    def _children_of(self, kind: ScopeKind) -> tuple[Any, ...]:
        return tuple(c for c in self._children if c.KIND == kind)

    def _iter_kind(self, kind: ScopeKind) -> Iterator[Any]:
        for child in self._children:
            if child.KIND == kind:
                yield child
            yield from child._iter_kind(kind)

    def _iter_callables(self) -> Iterator[Any]:
        return self._iter_kind(ScopeKind.CALLABLE)

    def _iter_classes(self) -> Iterator[Any]:
        return self._iter_kind(ScopeKind.CLASS)

    def _iter_modules(self) -> Iterator[Any]:
        return self._iter_kind(ScopeKind.MODULE)


class Callable(Scope):
    """A function, method or lambda: the leaf of the tree, and the scope the primitive
    complexity measures are taken at."""

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

    def parameters(self) -> tuple[str, ...]:
        """Declared parameter names, in order."""
        return self._parameters

    def nested(self) -> tuple[Any, ...]:
        """Callables defined inside this one."""
        return self._children_of(ScopeKind.CALLABLE)


class Class(Scope):
    """A class, interface, record, struct or enum: the scope the CK measures are taken at."""

    KIND = ScopeKind.CLASS

    def __init__(self, *, is_abstract: bool | None, bases: tuple[str, ...], **kw: Any) -> None:
        super().__init__(**kw)
        self._is_abstract = is_abstract
        self._base_names = bases
        self._properties: tuple[str, ...] | None = None

    @property
    def is_abstract(self) -> bool | None:
        """Whether this is an abstract type (interface, trait, abstract class); None when its
        grammar cannot tell. Martin's abstractness counts the classes that answer."""
        return self._is_abstract

    def methods(self) -> tuple[Any, ...]:
        """The callables declared in this class."""
        return self._children_of(ScopeKind.CALLABLE)

    def properties(self) -> tuple[str, ...]:
        """The fields this class declares (``slop.scope.properties``), read on first use."""
        if self._properties is None:
            from .properties import class_properties
            self._properties = class_properties(self)
        return self._properties


class Module(Scope):
    """An importable unit: one Python, JavaScript or Rust file; the files of one Go package."""

    KIND = ScopeKind.MODULE

    def imports(self):
        """The module's import declarations as written, before resolution
        (``slop.graph.imports``)."""
        from ..graph.imports import module_imports
        return module_imports(self)


class Package(Scope):
    """A group of modules inside a realm, as its language defines one (a Python directory with
    ``__init__.py``, a Go directory): the scope Martin's package metrics are taken at."""

    KIND = ScopeKind.PACKAGE

    def __init__(self, *, path: Path, **kw: Any) -> None:
        super().__init__(**kw)
        self._path = path

    @property
    def path(self) -> Path:
        """The package's directory."""
        return self._path

    def modules(self) -> tuple[Any, ...]:
        """The modules directly in this package."""
        return self._children_of(ScopeKind.MODULE)


class Realm(Scope):
    """The part of a corpus written in one language, with that language's grammar."""

    KIND = ScopeKind.REALM

    def __init__(self, *, root: Path, grammar: type, language: str, **kw: Any) -> None:
        super().__init__(**kw)
        self._root = root
        self._grammar = grammar
        self._language = language

    @property
    def root(self) -> Path:
        """The directory imports in this realm resolve from."""
        return self._root

    @property
    def grammar(self) -> type:
        """The grammar of this realm's language (``slop.ast.grammar``)."""
        return self._grammar

    @property
    def language(self) -> str:
        """The language id (``python``, ``go``, ...)."""
        return self._language

    def packages(self) -> tuple[Any, ...]:
        """The packages in this realm."""
        return self._children_of(ScopeKind.PACKAGE)


class Corpus(Scope):
    """Everything under the scanned root: the top of the tree, holding one realm per language
    and the analysis config."""

    KIND = ScopeKind.CORPUS

    def __init__(self, *, root: Path, config: Any, **kw: Any) -> None:
        super().__init__(**kw)
        self._root = root
        self._config = config

    @property
    def root(self) -> Path:
        """The scanned root."""
        return self._root

    @property
    def config(self):
        """The analysis config that governs this scan."""
        return self._config

    def realms(self) -> tuple[Any, ...]:
        """The realms found under the root, one per language."""
        return self._children_of(ScopeKind.REALM)
