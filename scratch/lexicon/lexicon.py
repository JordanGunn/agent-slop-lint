"""Lexicon — a scope-agnostic bag of Lexemes with statistical queries.

A Lexicon holds a tuple of ``Lexeme`` items and exposes the
queries that group-B rules (``imposters``, ``sprawl``,
``slackers``, ``confusion``) currently inline: token frequencies,
modal tokens, position-keyed alphabets, alphabet coverage, and
modal overlap.

Two design properties matter:

- **Scope-agnostic.** A Lexicon does not know about files,
  directories, clusters, or any other structural concept. Callers
  compose Lexicons by concatenating items: ``Lexicon(a + b)``.
- **No default filtering.** The Lexicon never silently drops
  tokens. Each query takes an optional ``exclude: frozenset[str]``
  argument; callers opt in to filtering for their analysis.

Queries are O(items) on first call per ``exclude`` set and O(1)
cached thereafter — the per-exclude filtered token view is held
in an instance dict.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Literal

from .lexeme import Lexeme


_Position = Literal["prefix", "suffix"]


class Lexicon:
    """A bag of Lexemes; statistical queries with per-call filtering."""

    def __init__(self, items: Iterable[Lexeme]) -> None:
        self.items: tuple[Lexeme, ...] = tuple(items)
        self._filtered_cache: dict[
            frozenset[str], tuple[tuple[str, ...], ...]
        ] = {}

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    # ---- internal: per-exclude filtered view -------------------------

    def _filtered(self, exclude: frozenset[str]) -> tuple[tuple[str, ...], ...]:
        cached = self._filtered_cache.get(exclude)
        if cached is not None:
            return cached
        out = tuple(
            tuple(t for t in lex.lower if t not in exclude)
            for lex in self.items
        )
        self._filtered_cache[exclude] = out
        return out

    # ---- queries ------------------------------------------------------

    def frequencies(
        self, exclude: frozenset[str] = frozenset(),
    ) -> Counter[str]:
        """Token-frequency counter over the (optionally filtered) bag."""
        c: Counter[str] = Counter()
        for toks in self._filtered(exclude):
            c.update(toks)
        return c

    def modal_tokens(
        self,
        k: int = 3,
        *,
        exclude: frozenset[str] = frozenset(),
    ) -> set[str]:
        """The top-``k`` most frequent tokens after filtering."""
        return {t for t, _ in self.frequencies(exclude).most_common(k)}

    def alphabet(
        self,
        position: _Position,
        *,
        exclude: frozenset[str] = frozenset(),
    ) -> Counter[str]:
        """Distribution of tokens at the leading or trailing position."""
        c: Counter[str] = Counter()
        for toks in self._filtered(exclude):
            if not toks:
                continue
            c[toks[0] if position == "prefix" else toks[-1]] += 1
        return c

    def coverage(
        self,
        alpha: set[str] | frozenset[str],
        position: _Position,
        *,
        exclude: frozenset[str] = frozenset(),
    ) -> float:
        """Fraction of items whose ``position`` token is in ``alpha``."""
        items = self._filtered(exclude)
        if not items:
            return 0.0
        hit = sum(
            1 for toks in items
            if toks
            and (toks[0] if position == "prefix" else toks[-1]) in alpha
        )
        return hit / len(items)

    def overlap(
        self,
        lexeme: Lexeme,
        modal: set[str] | frozenset[str],
        *,
        exclude: frozenset[str] = frozenset(),
    ) -> float:
        """Fraction of ``lexeme``'s tokens (after filter) that hit ``modal``."""
        my = {t for t in lexeme.lower if t not in exclude}
        if not my:
            return 0.0
        return len(my & modal) / len(my)
