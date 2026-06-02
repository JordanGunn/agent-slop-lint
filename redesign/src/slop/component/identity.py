"""Component identity and extent — the stable keys the whole model hangs on.

A component's identity is a value, not an object reference. tree-sitter node
identity is not stable across accesses, and the derived graphs
(DependencyGraph, CallGraph) must reference nodes durably, so every component is
keyed by ``(kind, qualname, extent spans)``.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..ast.span import Span  # re-exported: Span is an AST-layer primitive (see ast/span.py)


class ComponentKind(Enum):
    """The six entity kinds in the ownership hierarchy."""

    CORPUS = "corpus"
    REALM = "realm"
    PACKAGE = "package"
    MODULE = "module"
    CLASS = "class"
    CALLABLE = "callable"


class CallableKind(Enum):
    """The sub-kind of a Callable — lets rules filter (e.g. exclude lambdas from
    named-entity lexical rules) without inspecting AST. Names are paradigm-neutral.
    """

    FUNCTION = "function"        # free function (module-direct)
    METHOD = "method"            # class-bound, implicit receiver
    LAMBDA = "lambda"            # anonymous / inline
    CONSTRUCTOR = "constructor"  # __init__ / ctor / new
    ACCESSOR = "accessor"        # property getter/setter, where the language has them


@dataclass(frozen=True)
class Extent:
    """The source material a component owns.

    A Python module's extent is one file (one span covering it); a Go module's
    is several files sharing a ``package`` declaration; a class's may be several
    spans in languages with reopened/partial classes. ``spans`` is the
    authoritative ownership evidence; ``sources`` is the de-duplicated set of
    files those spans fall in, for convenience.
    """

    spans: tuple[Span, ...]

    @property
    def sources(self) -> tuple[Path, ...]:
        """Distinct source files this extent touches, in first-seen order."""
        ...


@dataclass(frozen=True)
class ComponentId:
    """Stable, hashable identity for a component.

    ``qualname`` is the dotted ownership path (``pkg.mod.Class.method``);
    ``spans`` disambiguates components that share a qualname (overloads,
    reopened classes). Equality and hashing are structural — two components with
    the same id are the same component, regardless of which traversal produced
    them.
    """

    kind: ComponentKind
    qualname: str
    spans: tuple[Span, ...]
