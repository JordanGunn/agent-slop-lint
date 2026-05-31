"""Projections — AST and Lexicon, lazy and bound to one component's extent.

Every component exposes two projections over its own extent:

    component.ast()      -> AST       parsed syntax (a subtree for a Callable,
                                       a forest for an aggregate)
    component.lexicon()  -> Lexicon   the cleaned identifier token-space

Design contract (locked here; internals deferred to build step 4):

- **One type each, not per-kind.** There is a single ``AST`` and a single
  ``Lexicon``; a component's projection differs only by *extent*, never by
  class. No ``CorpusLexicon`` / ``ModuleAST`` proliferation.
- **AST is the substrate; Lexicon derives from it.** A Lexicon is built by
  flattening the extent's AST, extracting identifier tokens, splitting
  camel/snake, lowercasing, and stripping stop-word noise — unioned with the
  component *names* in the extent (module/package names come from the
  filesystem, not an AST node; this carries the grammatical-degradation signal).
- **Lazy + sliceable.** Parsing happens once per file at the Corpus level; a
  component's projection is a *slice* of its owner's over the relevant
  spans/files, never a re-parse. ``slice`` narrows an existing projection to a
  sub-extent so child scopes reuse parent computation.
- **Cache-safe by construction.** Projections are pure functions of
  (extent, parse data), keyed by the component's stable ``ComponentId``, and
  immutable — so memoisation can be added later without redesign. Caching itself
  is deferred; we only avoid decisions hostile to it.

These are deliberately minimal: enough to establish that a component has an AST
to compute structural metrics from and a Lexicon to compute lexical metrics
from. We do NOT port the legacy view's method surface. The metric/rule layer
*consumes* these primitives — rules are not methods here (metric-vs-rule
separation).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .identity import Extent


@runtime_checkable
class AST(Protocol):
    """The parsed abstract syntax over a component's extent — one subtree for a
    Callable, a forest for an aggregate. Structural metrics walk it; it is never
    asked for a verdict.
    """

    def slice(self, extent: Extent) -> AST:
        """Narrow to a sub-extent without re-parsing (a child scope reuses its
        owner's parse rather than recomputing)."""
        ...


@runtime_checkable
class Lexicon(Protocol):
    """The cleaned identifier token-space over a component's extent.

    Derived from the AST (flatten → tokenize → split → strip noise) unioned with
    the component names in the extent. Exposes distribution *primitives*; the
    lexical metrics/rules (dispersion, stutter, sprawl, …) consume these and live
    in the metric/rule layer, not here.
    """

    def tokens(self) -> tuple[str, ...]:
        """Cleaned, noise-removed significant tokens over the extent."""
        ...

    def significant_token_count(self) -> int:
        """Distinct significant tokens after stop-word/noise removal — the
        namespace-maturity gate for dispersion."""
        ...

    def hapax_ratio(self) -> float:
        """Fraction of significant tokens occurring exactly once (a raw norm,
        ~0.49 invariant; deviation from baseline is the signal, not the value)."""
        ...

    def slice(self, extent: Extent) -> Lexicon:
        """Narrow to a sub-extent, reusing the parent's token computation."""
        ...
