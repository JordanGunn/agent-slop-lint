"""Aggregate containers — Corpus, Realm, Package.

These own components, not declarations. Their lexicon/ast projections and
their aggregatable complexity (via ``ComplexityMeasures`` on Component) are the
composition of their children's. Position-unique metrics: Package owns Martin's
package measures + runt detection; Corpus owns the analysis-wide measures
(orphans, duplication, hotspots, cycles). Realm is a pure aggregate plus the
grammar adapter and the resolver root.

Ownership of cross-cutting state, settled here:
- the analysis **config** lives on ``Corpus`` (the analysis boundary);
- the **grammar** adapter lives on ``Realm`` (the resolver world);
- **source-root detection** lives on ``Corpus.scan`` (it discovers Realms).
"""
from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from ..language import Grammar, Paradigm
from .base import AggregateContainer
from .identity import ComponentKind
from .measures import CorpusMeasures, PackageMeasures
from .symbol import Module

if TYPE_CHECKING:
    from ..config import AnalysisConfig


class Package(AggregateContainer, PackageMeasures):
    """An organizational namespace inside a Realm — a directory or import-path
    segment grouping Modules and sub-Packages.

    The home altitude for Martin's package metrics (``PackageMeasures``), which
    are undefined below a package. Typed convenience accessors (``classes()`` /
    ``functions()``) are gated by the owning Realm's grammar paradigm, not
    declared universally here.
    """

    KIND: ClassVar[ComponentKind] = ComponentKind.PACKAGE

    @property
    @abstractmethod
    def path(self) -> Path:
        """The package's namespace path (directory or import-path segment)."""
        ...

    @abstractmethod
    def packages(self) -> Sequence["Package"]:
        """Direct sub-packages."""
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

    KIND: ClassVar[ComponentKind] = ComponentKind.REALM

    @property
    @abstractmethod
    def root(self) -> Path:
        """The Realm's resolver root inside the Corpus."""
        ...

    @property
    @abstractmethod
    def grammar(self) -> type[Grammar]:
        """The grammar adapter for this Realm's language (the ported
        ``slop.language`` contract). The Realm is the layer that owns it."""
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


class Corpus(AggregateContainer, CorpusMeasures):
    """The filesystem root selected for analysis — an analysis boundary, not
    necessarily a real project root.

    Owns one or more Realms (polyglot repos have several), the analysis
    ``config``, and the ``scan`` that discovers Realms by detecting language
    source roots under ``root``. Owns no declarations; its projections are the
    union over its Realms.
    """

    KIND: ClassVar[ComponentKind] = ComponentKind.CORPUS

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

    @classmethod
    @abstractmethod
    def scan(cls, root: Path, config: AnalysisConfig) -> "Corpus":
        """Build a Corpus from a filesystem root: detect language source roots,
        construct one Realm per coherent resolver world, and carve the hierarchy
        beneath each. Source-root detection is Corpus-internal (private
        ``_detect_*`` helpers); polyglot roots yield multiple Realms."""
        ...

    @abstractmethod
    def realms(self) -> Sequence[Realm]:
        """The semantic code units discovered under the analysis root."""
        ...
