"""Identity primitives — the substrate's stable, value-typed keys.

Like :class:`~slop.span.Span`, these live at the package root and depend on nothing
above it: the scope model, the metric views, the dependency graph, and the
linter all key on them, so housing them low keeps those layers from depending on each
other just to share an id. ``slop.scope.identity`` re-exports them.

Logical vs physical identity: ``ScopeId`` carries a stable *logical* key (kind +
qualname) distinct from its *physical* extent (byte spans). A one-byte edit shifts the
spans but not the logical key, so cross-run diffing / caching / graph-keying should use
``ScopeId.logical`` where physical drift would otherwise break identity. Equality
and hashing remain structural over all fields (spans included) — the logical key is an
additional accessor, not a change to identity semantics.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .span import Span


class ScopeKind(Enum):
    """The six entity kinds in the ownership hierarchy."""

    CORPUS = "corpus"
    REALM = "realm"
    PACKAGE = "package"
    MODULE = "module"
    CLASS = "class"
    CALLABLE = "callable"


class CallableKind(Enum):
    """The sub-kind of a Callable — lets rules filter (e.g. exclude lambdas from
    named-entity lexical rules) without inspecting AST. Names are language-neutral.
    """

    FUNCTION = "function"        # free function (module-direct)
    METHOD = "method"            # class-bound, implicit receiver
    LAMBDA = "lambda"            # anonymous / inline
    CONSTRUCTOR = "constructor"  # __init__ / ctor / new
    ACCESSOR = "accessor"        # property getter/setter, where the language has them


@dataclass(frozen=True)
class Extent:
    """The source material a scope owns.

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
class ScopeId:
    """Stable, hashable identity for a scope.

    ``qualname`` is the dotted ownership path (``pkg.mod.Class.method``);
    ``spans`` disambiguates scopes that share a qualname (overloads,
    reopened classes). Equality and hashing are structural — two scopes with
    the same id are the same scope, regardless of which traversal produced
    them.
    """

    kind: ScopeKind
    qualname: str
    spans: tuple[Span, ...]

    @property
    def logical(self) -> tuple[ScopeKind, str]:
        """The stable logical key (kind + qualname), independent of byte spans.

        Use this for cross-run diffing, caching, or graph-keying where the physical
        spans drift under edits. Full ``ScopeId`` equality still includes spans
        (to disambiguate overloads / reopened classes within one analysis)."""
        return (self.kind, self.qualname)


def relative_path(scope_id: ScopeId, root: Path | str) -> str | None:
    """A scope's first source file relative to ``root``, or None if it carries no span.

    Module bare-stem qualnames collide across packages (``octree/index.py`` and
    ``quadtree/index.py`` are both ``index``), so the path is what addresses a module."""
    if scope_id.spans and scope_id.spans[0].path:
        try:
            return os.path.relpath(scope_id.spans[0].path, root)
        except ValueError:
            return scope_id.spans[0].path
    return None
