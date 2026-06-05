"""The Lexicon projection — lazy, bound to one component's extent.

Each component exposes one projection over its own extent:

    component.lexicon()  -> Lexicon   the cleaned identifier token-space

The *AST* is no longer a per-component projection. It is the first-class
``slop.ast`` proxy (``AST`` + ``Node``): one ``AST`` per file, and a component
reaches its own subtree as a ``Node`` (composition over files for aggregates).
Carving holds the nodes; metrics walk the proxy. This keeps raw tree-sitter
isolated to ``slop.ast`` and avoids a second, forest-shaped AST abstraction here.

Design contract (the Lexicon half, still locked):

- **One type, not per-kind.** There is a single ``Lexicon``; a component's
  projection differs only by *extent*, never by class. No ``CorpusLexicon`` /
  ``ModuleLexicon`` proliferation.
- **Derived from the AST proxy.** A Lexicon is built by walking the extent's
  ``slop.ast`` nodes, extracting identifier tokens, splitting camel/snake,
  lowercasing, and stripping stop-word noise — unioned with the component
  *names* in the extent (module/package names come from the filesystem, not an
  AST node; this carries the grammatical-degradation signal).
- **Lazy + sliceable by span.** ``slice`` narrows an existing projection to a
  sub-extent (matched on the extent's span paths), so child scopes reuse parent
  computation rather than re-deriving.
- **Cache-safe by construction.** Pure function of (extent, parse data), keyed
  by the component's stable ``ScopeId``, and immutable — memoisation can be
  added later without redesign.

The metric/rule layer *consumes* this primitive — rules are not methods here
(metric-vs-rule separation).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..lexicon import TokenDistribution
    from .identity import Extent


@runtime_checkable
class Lexicon(Protocol):
    """The cleaned identifier token-space over a component's extent.

    Derived from the ``slop.ast`` proxy (walk → tokenize → split → strip noise)
    unioned with the component names in the extent. Exposes distribution
    *primitives*; the lexical metrics/rules (dispersion, stutter, sprawl, …)
    consume these and live in the metric/rule layer, not here.
    """

    def tokens(self) -> tuple[str, ...]:
        """Cleaned, noise-removed significant tokens over the extent."""
        ...

    def significant_token_count(self) -> int:
        """Distinct significant tokens after stop-word/noise removal — the
        namespace-maturity gate for dispersion."""
        ...

    def total_token_count(self) -> int:
        """Total significant token occurrences, with multiplicity."""
        ...

    def hapax_ratio(self) -> float:
        """Fraction of significant tokens occurring exactly once (a raw norm,
        ~0.49 invariant; deviation from baseline is the signal, not the value)."""
        ...

    def most_common(self, n: int = 15) -> list[tuple[str, int]]:
        """The ``n`` most frequent significant tokens, as ``(token, count)``."""
        ...

    def distribution(self, *, top: int = 15) -> TokenDistribution:
        """The token-space as a measured Zipfian distribution (claim-free) — the
        object the ``vocabulary`` observation surfaces."""
        ...

    def slice(self, extent: Extent) -> Lexicon:
        """Narrow to a sub-extent (matched on the extent's span paths), reusing
        the parent's token computation."""
        ...
