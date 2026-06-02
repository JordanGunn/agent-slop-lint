"""Identity primitives — the substrate's stable, value-typed keys.

Like :class:`~slop.span.Span`, these live at the package root and depend on nothing
above it: the scope model, the metric views, the dependency/call graphs, and the
linter all key on them, so housing them low keeps those layers from depending on each
other just to share an id. ``component.identity`` re-exports them so existing
``from ..scope.identity import …`` sites are unchanged.

Logical vs physical identity: ``ComponentId`` carries a stable *logical* key (kind +
qualname) distinct from its *physical* extent (byte spans). A one-byte edit shifts the
spans but not the logical key, so cross-run diffing / caching / graph-keying should use
``ComponentId.logical`` where physical drift would otherwise break identity. Equality
and hashing remain structural over all fields (spans included) — the logical key is an
additional accessor, not a change to identity semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .span import Span


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

    @property
    def logical(self) -> tuple[ComponentKind, str]:
        """The stable logical key (kind + qualname), independent of byte spans.

        Use this for cross-run diffing, caching, or graph-keying where the physical
        spans drift under edits. Full ``ComponentId`` equality still includes spans
        (to disambiguate overloads / reopened classes within one analysis)."""
        return (self.kind, self.qualname)
