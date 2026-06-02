"""Symbol containers — Module, Class, Callable.

These own declarations directly. Structural ownership (what's inside) is
declared here; the *metrics* each kind owns come from the measure mixins in
``measures.py``, so this file stays about structure and the metric inventory
stays in one ledger.

    Callable : ComplexityMeasures (inherited) + CallableMeasures
    Class    : ComplexityMeasures (inherited) + ClassMeasures
    Module   : ComplexityMeasures (inherited) + ModuleMeasures
"""
from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from typing import ClassVar

from .base import SymbolContainer
from .identity import CallableKind, ComponentKind
from .measures import CallableMeasures, ClassMeasures, ModuleMeasures
from .metrics import ImportDecl


class Callable(SymbolContainer, CallableMeasures):
    """A function or method — the leaf of the hierarchy and the home altitude
    for the primitive structural metrics.

    Owns its parameters, locals, and nested callables. ``cyclomatic`` etc. come
    from ``ComplexityMeasures`` (via Component); the non-aggregatable extras
    (full Halstead, density, magic literals, mutations, sentinels) come from
    ``CallableMeasures``.
    """

    KIND: ClassVar[ComponentKind] = ComponentKind.CALLABLE

    @property
    @abstractmethod
    def kind(self) -> CallableKind:
        """Function / method / lambda / constructor / accessor — lets rules
        filter without inspecting AST (e.g. exclude lambdas from named entities)."""
        ...

    @abstractmethod
    def parameters(self) -> Sequence[str]:
        """Declared parameter names, in order."""
        ...

    @abstractmethod
    def locals(self) -> Sequence[str]:
        """Names bound in the callable's own body."""
        ...

    @abstractmethod
    def nested(self) -> Sequence["Callable"]:
        """Callables defined inside this one (closures, local functions)."""
        ...


class Class(SymbolContainer, ClassMeasures):
    """A class/interface/record/enum — a nested symbol container owning methods,
    properties, and child types.

    The home altitude for the CK suite (``ClassMeasures``). Produced only by
    adapters for object-oriented languages; languages without classes do not
    emit Class components — class-bearing-ness is gated by the Realm's grammar paradigm
    (``ast.Paradigm``), the single source of truth for which symbol kinds exist.
    """

    KIND: ClassVar[ComponentKind] = ComponentKind.CLASS

    @property
    @abstractmethod
    def is_abstract(self) -> bool:
        """Abstract (interface/trait/ABC/abstract class) vs concrete. The
        per-class signal that `Package` abstractness (Martin's A) aggregates;
        supplied by the grammar adapter's abstractness classification."""
        ...

    @abstractmethod
    def methods(self) -> Sequence["Callable"]:
        """Callables owned by this class."""
        ...

    @abstractmethod
    def properties(self) -> Sequence[str]:
        """Declared fields/properties."""
        ...

    @abstractmethod
    def bases(self) -> Sequence["Class"]:
        """Resolved superclasses, where in-corpus and resolvable."""
        ...

    @abstractmethod
    def nested_classes(self) -> Sequence["Class"]:
        """Classes declared inside this class."""
        ...


class Module(SymbolContainer, ModuleMeasures):
    """The primary symbol container — an importable/buildable unit.

    Not always one file: Python maps one ``.py`` to one Module; Go maps a
    directory of files sharing a ``package`` declaration to one.

    Declarations are reached uniformly via ``symbols()``. The typed accessors —
    ``functions()`` / ``constants()`` / ``classes()`` — are deliberately NOT on
    this base: they are paradigm-gated (functions/constants for Procedural and
    MultiPurpose grammars; classes for ObjectOriented and MultiPurpose), so a
    pure-OO module is never forced to return an empty free-function list. They
    will be added as paradigm-aligned accessors when the grammar hierarchy ports
    (see ``slop.ast``). Module-level and within-module relational metrics
    come from ``ModuleMeasures``.
    """

    KIND: ClassVar[ComponentKind] = ComponentKind.MODULE

    @abstractmethod
    def imports(self) -> Sequence[ImportDecl]:
        """Raw, pre-resolution import declarations; resolved into DependencyGraph edges."""
        ...
