"""Lexeme + Lexicon + ignore-list constants.

The substrate the four group-B lexical rules (``imposters``,
``sprawl``, ``slackers``, ``confusion``) consume for their
identifier-token analysis. Group-A rules (``verbosity``,
``cowards``, ``tautology``, ``hammers``, ``stutter``) operate
per-name and continue to use ``split_identifier`` directly — they
do not need a Lexicon.

A ``Lexeme`` is one tokenised identifier, frozen and hashable,
cheap to share across any number of Lexicons. A ``Lexicon`` is a
scope-agnostic bag of Lexemes with statistical queries; it does
NOT filter tokens by default — filtering is a per-query opt-in
via the ``exclude=`` argument. See
``docs/research/identifier-vocabulary.md`` for the layered ignore
model and the literature behind ``UNIVERSAL_NOISE``.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Literal

from slop._lexical._naming import split_identifier


# ---------------------------------------------------------------------------
# Ignore-list constants
# ---------------------------------------------------------------------------


# Newman, AlSuhaibani, Collard & Maletic (SANER 2017), "Lexical
# Categories for Source Code Identifiers." 14 identifiers found in
# all 50 OSS C/C++ systems they studied (480K unique identifiers).
# Empirical cross-corpus universal noise from identifier streams.
_NEWMAN_14: frozenset[str] = frozenset({
    "a", "length", "id", "pos", "start", "next", "str", "key",
    "f", "x", "index", "p", "left", "result",
})


# English structure words that appear inside identifier streams as
# glue between meaningful tokens (``count_of_items``, ``data_for_id``).
_GLUE: frozenset[str] = frozenset({
    "the", "an", "is", "are", "to", "for", "in", "on", "of",
    "with", "by", "as", "at", "and", "or", "but", "if",
})


UNIVERSAL_NOISE: frozenset[str] = _NEWMAN_14 | _GLUE
"""Layer 1 + Layer 3 of the layered ignore model — the only ignore
set shipped in v1. SE-boilerplate (Layer 2: ``manager``, ``helper``,
...) is deliberately excluded — that vocabulary is the signal
``lexical.hammers`` exists to detect. Per-language ecosystem idioms
(Layer 4) are deferred to ``docs/backlog/09.md``."""


# ---------------------------------------------------------------------------
# Lexeme
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Lexeme:
    """One tokenised identifier.

    ``text`` is the source-form (e.g. ``"get_user_email"``).
    ``tokens`` is the snake/Camel-split sequence in original case.
    ``lower`` is the same sequence case-folded. ``file`` and
    ``line`` are optional metadata for callers that surface
    findings against the original code location.
    """

    text: str
    tokens: tuple[str, ...]
    lower: tuple[str, ...]
    file: str | None = None
    line: int | None = None

    @classmethod
    def of(
        cls,
        text: str,
        *,
        file: str | None = None,
        line: int | None = None,
    ) -> "Lexeme":
        """Build a Lexeme by tokenising ``text`` once."""
        toks = tuple(split_identifier(text))
        return cls(
            text=text,
            tokens=toks,
            lower=tuple(t.lower() for t in toks),
            file=file,
            line=line,
        )


# ---------------------------------------------------------------------------
# Lexicon
# ---------------------------------------------------------------------------


_Position = Literal["prefix", "suffix"]


class Lexicon:
    """A scope-agnostic bag of Lexemes with statistical queries.

    Composition is concatenation: ``Lexicon(items_a + items_b)``.
    The Lexicon never silently drops tokens; each query takes an
    optional ``exclude: frozenset[str]`` argument so callers opt
    in to filtering for their analysis.

    Queries are O(items) on first call per ``exclude`` set and
    O(1) cached thereafter (per-exclude filtered view held in an
    instance dict).
    """

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
