"""The Scope spine — base ABC and the two container tiers.

``Scope`` is the root of the ownership model: a named, identity-bearing region of
source (Corpus through Callable). The term is reclaimed deliberately — the legacy v2
``Scope`` (a parse record + enum) does not exist in this tree, so there is no clash.

    Scope
      AggregateContainer   (Corpus | Realm | Package)  -- own child scopes
      SymbolContainer      (Module | Class | Callable)  -- own declarations
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from .identity import ScopeId, ScopeKind, Extent
from .projection import Lexicon


class Scope(ABC):
    """The shared interface every scope component satisfies — the single source
    of truth for what is universal across the hierarchy.

    If a method or property is unanimous across all six kinds (Corpus through
    Callable), it lives here and nowhere else. That is: ``KIND`` (a class
    constant, so identity/dispatch never re-derive it), a stable identity,
    ``name``/``qualname``, an extent, the files it spans, an owner (None only for
    the Corpus root), child components, the lazy ``lexicon()`` projection over its
    own extent, and the aggregatable complexity surface (``ComplexityMeasures`` —
    primitive at the Callable leaf, summed at every container). Anything
    non-universal — declaration ownership (``SymbolContainer``) and position-unique
    metrics — is declared one tier down, never here.

    The parsed AST is no longer a per-component projection: it is the
    ``slop.ast`` proxy (``AST``/``Node``), reached from a component's carved
    nodes. Rules consume ``lexicon()`` and the metric surface, not AST nodes.
    """

    #: The entity kind this class represents; set on every concrete kind so
    #: ``id``/dispatch/filtering key on a constant rather than runtime checks.
    KIND: ClassVar[ScopeKind]

    @property
    @abstractmethod
    def id(self) -> ScopeId:
        """Stable, hashable identity. Equality is structural, not by reference."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """The component's local (simple) name — the last segment of ``qualname``."""
        ...

    @property
    def qualname(self) -> str:
        """The full dotted ownership path. Single source of truth is
        ``id.qualname``; this is the universal convenience accessor over it."""
        return self.id.qualname

    @property
    @abstractmethod
    def owner(self) -> Scope | None:
        """The containing component, or None for the Corpus root."""
        ...

    @property
    @abstractmethod
    def extent(self) -> Extent:
        """The source material this component owns."""
        ...

    @property
    @abstractmethod
    def files(self) -> tuple[Path, ...]:
        """Distinct files this component spans (the file side of its extent).

        Cardinality is language-dependent and is itself a signal: a Python
        Module has exactly one file; a Go Module has many (its package
        directory); a C++ Class may span a header/source pair. Aggregate
        containers expose the union over their descendants — the basis for
        file-tree rendering and grouping findings by file.
        """
        ...

    @abstractmethod
    def children(self) -> Sequence[Scope]:
        """Direct child components in the ownership hierarchy."""
        ...

    @abstractmethod
    def lexicon(self) -> Lexicon:
        """Cleaned identifier token-space over this component's extent (lazy).
        Derived from the ``slop.ast`` proxy over the extent plus the component
        names in the extent."""
        ...


class AggregateContainer(Scope, ABC):
    """Owns other components; every projection is an aggregate of children.

    Aggregate containers own no declarations directly. Their lexicon and
    ast are the composition of their children's — the recursive base case
    is always the tier directly below. Corpus, Realm, and Package live here.
    """


class SymbolContainer(Scope, ABC):
    """Owns declarations directly.

    Module, Class, and Callable live here. Rules that need declaration
    ownership target a SymbolContainer kind, never an arbitrary scope string.
    """

    @abstractmethod
    def symbols(self) -> Sequence[Scope]:
        """Declarations owned directly by this container (callables, nested
        types, and — where the language supports them — classes)."""
        ...
