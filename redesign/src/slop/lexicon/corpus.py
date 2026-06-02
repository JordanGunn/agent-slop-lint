"""Lexicon — the analysable identifier token-space over some extent.

The kernel's central object: a bag of role-tagged, span-located identifier tokens,
cleaned (split, lowercased, stop-word stripped) and ready for descriptive
measurement. There is **one** ``Lexicon`` type; a narrower scope is a narrower
*extent*, never a subclass — ``slice`` produces a sub-lexicon over a path subset,
reusing the parent's tokenisation.

Boundary discipline: this module measures the token-space and nothing more. Type and
token counts, hapax ratio, and frequency are descriptive lexicostatistics a corpus
linguist would recognise. Thresholds, verdicts, and slop's named metrics live in the
rule layer above; none belong here.

Input is plain data — a stream of ``(text, role, span)`` — so the lexicon imports
nothing from ``component``/``rules``/``linter`` and stays usable on its own. ``slice``
is duck-typed on its argument's ``.spans`` (each exposing ``.path``) precisely so the
component ``Extent`` type need not be imported.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from ..span import Span
from .distribution import TokenDistribution, token_distribution
from .roles import Role
from .stopwords import STOP_WORDS
from .tokenize import Lexeme


class Lexicon:
    """A cleaned, role-tagged identifier token-space.

    Built from a stream of ``(text, role, span)`` units. Each unit is tokenised
    once into a :class:`Lexeme`; the significant token-space is the lowercased
    tokens with stop words removed, retaining provenance for slicing and future
    cross-view joins.
    """

    def __init__(
        self,
        units: Iterable[tuple[str, Role, Span]],
        *,
        stopwords: frozenset[str] | set[str] = STOP_WORDS,
    ) -> None:
        self._units: list[tuple[str, Role, Span]] = list(units)
        self._stopwords = stopwords
        self._lexemes: list[Lexeme] = [
            Lexeme.of(text, role=role, span=span) for text, role, span in self._units
        ]
        # Significant tokens: lowercased, stop-word stripped, provenance retained.
        self._tokens: list[tuple[str, Role, Span]] = []
        for lex in self._lexemes:
            for low in lex.lower:
                if low and low not in stopwords:
                    self._tokens.append((low, lex.role, lex.span))
        self._counter: Counter[str] = Counter(t for t, _, _ in self._tokens)

    # ---- descriptive measurements ------------------------------------
    def tokens(self) -> tuple[str, ...]:
        """Distinct significant tokens, sorted."""
        return tuple(sorted(self._counter))

    def significant_token_count(self) -> int:
        """Distinct significant tokens after stop-word removal."""
        return len(self._counter)

    def total_token_count(self) -> int:
        """Total significant token occurrences (with multiplicity)."""
        return sum(self._counter.values())

    def hapax_ratio(self) -> float:
        """Fraction of distinct tokens occurring exactly once."""
        n = len(self._counter)
        if n == 0:
            return 0.0
        return sum(1 for c in self._counter.values() if c == 1) / n

    def most_common(self, n: int = 15) -> list[tuple[str, int]]:
        """The ``n`` most frequent significant tokens, as ``(token, count)``."""
        return self._counter.most_common(n)

    def frequencies(self) -> dict[str, int]:
        """Significant token -> occurrence count."""
        return dict(self._counter)

    def distribution(self, *, top: int = 15) -> TokenDistribution:
        """This token-space as a measured Zipfian distribution (claim-free; the
        object the ``vocabulary`` observation surfaces). See
        :mod:`slop.lexicon.distribution`."""
        return token_distribution(self._counter, top=top)

    # ---- corpus selection --------------------------------------------
    def slice(self, extent: Any) -> "Lexicon":
        """Narrow to a sub-extent, matched on span paths. ``extent`` is any object
        exposing ``.spans`` (each with a ``.path``); duck-typed so the component
        ``Extent`` type stays out of this layer. Reuses the parent's units."""
        paths = {span.path for span in extent.spans}
        return Lexicon(
            [u for u in self._units if u[2].path in paths],
            stopwords=self._stopwords,
        )
