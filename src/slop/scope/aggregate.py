"""Aggregate containers — Corpus, Realm, Package.

These own components, not declarations. Their lexicon/ast projections are the
composition of their children's; measurements over them come from
``Structure.over(region)`` (the entity stays pure ownership). Package owns Martin's
package measures; Corpus owns the analysis-wide measures (duplication,
cycles). Realm is a pure aggregate plus the grammar adapter and the resolver
root.

Ownership of cross-cutting state, settled here:
- the analysis **config** lives on ``Corpus`` (the analysis boundary);
- the **grammar** adapter lives on ``Realm`` (the resolver world);
- **source-root detection** lives in ``carve.scan_corpus`` (it discovers Realms).
"""
from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from ..ast import Grammar, Paradigm
from .base import AggregateContainer
from .identity import ScopeKind
from .symbol import Module

if TYPE_CHECKING:
    from ..config import AnalysisConfig


class Package(AggregateContainer):
    """An organizational namespace inside a Realm — a directory or import-path
    segment grouping Modules. Packages are siblings under a Realm, never nested in each other.

    The home altitude for Martin's package metrics (``PackageMeasures``), which
    are undefined below a package. Typed convenience accessors (``classes()`` /
    ``functions()``) are gated by the owning Realm's grammar paradigm, not
    declared universally here.
    """

    KIND: ClassVar[ScopeKind] = ScopeKind.PACKAGE

    @property
    @abstractmethod
    def path(self) -> Path:
        """The package's namespace path (directory or import-path segment)."""
        ...

    @abstractmethod
    def modules(self) -> Sequence[Module]:
        """Modules directly in this package."""
        ...


class Realm(AggregateContainer):
    """A single language/sdk resolver world inside a Corpus — the source-code
    root of one application component, homogeneous in language.

    Owns the grammar adapter; this is the layer that owns grammars. The
    grammar's ``paradigm`` decides which typed accessors the Realm's carved
    Modules/Packages expose. Per-language carving is delegated to the grammar,
    never branched on inside the hierarchy. A filesystem-anchored entity: it
    keeps a ``root``, owns the grammar/language, and exposes its file tree.
    """

    KIND: ClassVar[ScopeKind] = ScopeKind.REALM

    @property
    @abstractmethod
    def root(self) -> Path:
        """The Realm's resolver root inside the Corpus."""
        ...

    @property
    @abstractmethod
    def grammar(self) -> type[Grammar]:
        """The grammar adapter for this Realm's language (the ported
        ``slop.ast`` contract). The Realm is the layer that owns it."""
        ...

    @property
    def paradigm(self) -> Paradigm:
        """The grammar's paradigm — drives capability gating for carved
        components. Derived from ``grammar``; not independently settable."""
        return self.grammar.PARADIGM

    @property
    @abstractmethod
    def language(self) -> str:
        """The resolver family identifier (e.g. ``python``, ``go``)."""
        ...

    @abstractmethod
    def packages(self) -> Sequence[Package]:
        """Top-level packages in this Realm."""
        ...


class Corpus(AggregateContainer):
    """The filesystem root selected for analysis — an analysis boundary, not
    necessarily a real project root.

    Owns one or more Realms (polyglot repos have several) and the analysis ``config``.
    Owns no declarations; its projections are the union over its Realms.
    """

    KIND: ClassVar[ScopeKind] = ScopeKind.CORPUS

    @property
    @abstractmethod
    def root(self) -> Path:
        """The scanned filesystem root (the analysis boundary)."""
        ...

    @property
    @abstractmethod
    def config(self) -> AnalysisConfig:
        """The analysis configuration governing this scan and the rules over it."""
        ...

    @abstractmethod
    def realms(self) -> Sequence[Realm]:
        """The semantic code units discovered under the analysis root."""
        ...
