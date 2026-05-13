"""Record dataclasses for the v2.0 substrate.

Pure-data identifiers produced by ``Tree`` while walking the
parsed corpus. Each record is hashable, picklable, free of circular
structures. Records do NOT carry the file's language — that's
denormalised state owned by the views' internal ``path → language``
index, built from each ``ParseResult.language``.

``Scope`` and ``Callable`` carry their parent qualname as a string
(not an object back-reference); views resolve parent lookups through
their indexed maps.

``ParseResult`` is an INTERNAL PIPELINE OBJECT — produced one-per-file
by ``Tree``'s walker, consumed by the view-construction step.
It carries ``callable_nodes`` and ``content`` for the views to power
their compute methods (e.g. ``Structure.cyclomatic``). Rules never
see ParseResult.

The ``Slop`` finding type lives in ``slop.linter.slop``, NOT here —
it's output-side, semantically distinct from parse entities.

See ``docs/planning/codebase.md`` for the locked design.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ScopeKind(str, Enum):
    """Kinds of named scopes a grammar can emit.

    ``FILE`` covers single-file-as-module languages (Python, JS, TS,
    Ruby) where the file itself is the addressable scope; ``MODULE``
    is reserved for languages with explicit module declarations (Go
    package, Rust mod, Julia module). ``NAMESPACE`` covers C++/C#
    namespace nodes; Tree-sitter dispatches to it via the grammar's
    future ``namespaces()`` declaration when a rule needs them.
    """

    FILE = "file"
    MODULE = "module"
    PACKAGE = "package"
    NAMESPACE = "namespace"
    CLASS = "class"
    INTERFACE = "interface"
    STRUCT = "struct"
    TRAIT = "trait"
    IMPL = "impl"


class CallableKind(str, Enum):
    """Kinds of callable definitions a grammar can emit.

    ``METHOD`` denotes a callable with an implicit receiver (Python's
    ``self``, Go's receiver, Ruby's ``self``, etc.). ``FUNCTION`` is
    receiver-free. ``LAMBDA`` is anonymous. ``CONSTRUCTOR`` is the
    language's syntactic constructor form (Java/C# ``ClassName()``,
    JS ``constructor()``, Python ``__init__``).
    """

    FUNCTION = "function"
    METHOD = "method"
    LAMBDA = "lambda"
    CONSTRUCTOR = "constructor"


@dataclass(frozen=True)
class Parameter:
    """One callable parameter.

    ``annotation`` is the source text of the type annotation (or None
    if absent). ``position`` is 0-indexed, including the implicit
    receiver for methods (Python ``self`` is position 0).
    """

    name: str
    position: int
    annotation: str | None = None


@dataclass(frozen=True)
class Scope:
    """A named scoping container — file, module, package, namespace,
    class-like.

    ``qualname`` is the dotted-path identity used as the key for parent
    lookups and slicing axes. ``parent`` is the qualname of the
    enclosing scope (None for top-level).
    """

    qualname: str
    kind: ScopeKind
    path: Path
    line: int
    end_line: int
    parent: str | None


@dataclass(frozen=True)
class Callable:
    """A callable definition — function, method, lambda, constructor.

    ``parent`` is the qualname of the enclosing scope (None for
    top-level free functions in single-file-module languages).
    ``parameters`` is the full parameter list including the implicit
    receiver for methods.
    """

    qualname: str
    kind: CallableKind
    path: Path
    line: int
    end_line: int
    parent: str | None
    parameters: tuple[Parameter, ...]


@dataclass(frozen=True)
class Occurrence:
    """One identifier or token occurrence in source.

    Used by the Lexicon view to expose ``walk()`` over every observed
    token in the corpus. ``kind`` discriminates ``"identifier"`` vs
    ``"comment"`` vs ``"string"`` etc. — concrete grammars decide
    which kinds they emit.
    """

    token: str
    path: Path
    line: int
    col: int
    scope: str | None
    callable: str | None
    kind: str


@dataclass(frozen=True)
class ParseResult:
    """Internal pipeline object — one file's parsed shape.

    Produced by ``Tree``'s walker for each scanned file; consumed
    by the view-construction step. NOT a public type; rules never see
    it.

    ``language`` is the canonical home of the file→language mapping;
    views use it to populate their internal ``path → language`` index.

    ``callable_nodes`` and ``content`` carry the grammar's raw AST
    data, used by the views' compute methods. They are internal to
    views; rules never see them.
    """

    path: Path
    language: str
    scopes: tuple[Scope, ...]
    callables: tuple[Callable, ...]
    occurrences: tuple[Occurrence, ...]
    callable_nodes: dict[str, Any] = field(default_factory=dict)
    scope_nodes: dict[str, Any] = field(default_factory=dict)
    content: bytes = b""
