"""Lexicon: the words of a set of identifiers, counted.

A bag of role-tagged, span-located identifier tokens, split, stop-word stripped and stemmed.
It measures the bag (type and token counts, hapax ratio, frequency, spread over files) and
checks nothing; limits belong to the rules.

Input is plain data, a stream of ``(text, role, span)``, so the lexicon imports nothing from
``scope``, ``rules`` or ``cli``.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import Iterable

from ..span import Span
from .distribution import TokenDistribution, token_distribution
from .roles import Role
from .inflection import stem
from .stopwords import STOP_WORDS
from .tokenize import Lexeme


class Lexicon:
    """A cleaned, role-tagged identifier token-space.

    Built from a stream of ``(text, role, span)`` units. Each unit is tokenised
    once into a :class:`Lexeme`; the significant token-space is the tokens that are
    not stop words, each counted under its stem (``slop.lexicon.inflection``, so
    ``node`` and ``Nodes`` are one word), keeping each token's role and span.
    """

    def __init__(
        self,
        units: Iterable[tuple[str, Role, Span]],
        *,
        stopwords: frozenset[str] | set[str] = STOP_WORDS,
    ) -> None:
        self._lexemes: list[Lexeme] = [Lexeme.of(text, role=role, span=span) for text, role, span in units]
        self._tokens: list[tuple[str, Role, Span]] = []
        for lex in self._lexemes:
            for token in lex.tokens:
                if token.lower() not in stopwords:
                    self._tokens.append((stem(token), lex.role, lex.span))
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

    def spread(self) -> dict[str, int]:
        """Significant token -> number of distinct files it occurs in (document
        frequency). Units with no file (a fileless component name) count in
        ``frequencies`` but in no file."""
        files: dict[str, set[str]] = {}
        for token, _role, span in self._tokens:
            if span.path:
                files.setdefault(token, set()).add(span.path)
        return {token: len(paths) for token, paths in files.items()}

    def ranked(self) -> list[str]:
        """Significant tokens, most used first, then in the most files, then alphabetically."""
        frequencies, spread = self.frequencies(), self.spread()
        return sorted(frequencies, key=lambda t: (-frequencies[t], -spread.get(t, 0), t))

    def spellings(self) -> dict[str, str]:
        """Significant token -> the spelling the code uses for it most often (``Laz`` for
        ``laz`` when ``LazReader`` and ``laz_path`` and ``LazHeader`` occur, ``node`` for
        ``node`` when ``node`` occurs more often than ``nodes``); ties go to the alphabetically
        first."""
        counts: dict[str, dict[str, int]] = {}
        for lexeme in self._lexemes:
            for token in lexeme.tokens:
                key = stem(token)
                if key in self._counter:
                    seen = counts.setdefault(key, {})
                    seen[token] = seen.get(token, 0) + 1
        return {key: min(seen, key=lambda t: (-seen[t], t)) for key, seen in counts.items()}

    def distribution(self, *, top: int = 15) -> TokenDistribution:
        """This token-space as a measured Zipfian distribution, its top words in the code's
        spelling. See :mod:`slop.lexicon.distribution`."""
        measured = token_distribution(self._counter, top=top)
        spellings = self.spellings()
        return replace(measured, top=[(spellings.get(t, t), c) for t, c in measured.top])
