"""Observed vocabulary against a canonical vocabulary, at the level of word tokens.

``vocab`` compares whole class names with the ontology's entities. This compares the
*words* the code actually uses, everywhere an identifier appears (class, function,
parameter, local, attribute), with the words the ontology defines. Four facts, none of
them a judgment:

- ``covered``: observed tokens the vocabulary defines.
- ``undefined``: observed tokens it does not define, most used first. This is the list
  that shows vocabulary the ontology has not named yet.
- ``unused``: canonical tokens the code never uses.
- ``unmeasurable``: canonical tokens the Lexicon's noise list strips before measurement
  (``key``, ``index``, ``result`` ...). They can never be observed, so reporting them
  as unused would be wrong.

There are no thresholds here. ``undefined`` is ordered, not filtered; how long a prefix
of it matters is the reader's call. The canonical tokens are the words of term names and
field keys; descriptions are prose and are not tokenised.
"""
from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from ..lexicon import STOP_WORDS, Lexicon, split_tokens
from ..ontology import Vocabulary


@dataclass(frozen=True)
class Observed:
    """One token as the code uses it: how often, and in how many files."""

    token: str
    count: int
    files: int
    defined_by: tuple[str, ...] = ()   # the canonical terms that contain this word, if any

    def as_dict(self) -> dict:
        return {"token": self.token, "count": self.count, "files": self.files,
                "defined_by": list(self.defined_by)}


@dataclass(frozen=True)
class Coverage:
    vocabulary: str
    covered: tuple[Observed, ...]
    undefined: tuple[Observed, ...]
    unused: tuple[str, ...]
    unmeasurable: tuple[str, ...]

    @property
    def occurrences_total(self) -> int:
        return sum(o.count for o in self.covered) + sum(o.count for o in self.undefined)

    @property
    def occurrences_covered(self) -> int:
        return sum(o.count for o in self.covered)

    def as_dict(self, *, top: int | None = None) -> dict:
        undefined = self.undefined if top is None else self.undefined[:top]
        return {
            "vocabulary": self.vocabulary,
            "occurrences": {"total": self.occurrences_total, "covered": self.occurrences_covered},
            "tokens": {"observed": len(self.covered) + len(self.undefined),
                       "covered": len(self.covered)},
            "covered": [o.as_dict() for o in self.covered],
            "undefined": [o.as_dict() for o in undefined],
            "undefined_total": len(self.undefined),
            "unused": list(self.unused),
            "unmeasurable": list(self.unmeasurable),
        }


def canonical_tokens(vocabulary: Vocabulary) -> dict[str, tuple[str, ...]]:
    """Each word the vocabulary defines -> the terms that contain it (names and field keys)."""
    owners: dict[str, set[str]] = {}
    for term in vocabulary.terms():
        words = list(split_tokens(term.name.replace("-", "_")))
        for key in term.fields:
            for part in key.split("/"):
                words.extend(split_tokens(part.replace("-", "_")))
        for word in words:
            owners.setdefault(word.lower(), set()).add(term.name)
    return {word: tuple(sorted(names)) for word, names in sorted(owners.items())}


def coverage(lexicon: Lexicon, vocabulary: Vocabulary, *,
             stopwords: Collection[str] = STOP_WORDS) -> Coverage:
    """Compare ``lexicon`` (observed) with ``vocabulary`` (canonical).

    Raises when nothing was observed: with no tokens, "everything is covered" and
    "nothing is undefined" would both be vacuously true."""
    frequencies = lexicon.frequencies()
    if not frequencies:
        raise ValueError("no identifier tokens were observed, so the comparison would be vacuous")
    canonical = canonical_tokens(vocabulary)
    if not canonical:
        raise ValueError(f"{vocabulary.name} defines no words to compare against")
    spread = lexicon.spread()

    def observed(token: str) -> Observed:
        return Observed(token, frequencies[token], spread.get(token, 0), canonical.get(token, ()))

    ranked = sorted(frequencies, key=lambda t: (-frequencies[t], -spread.get(t, 0), t))
    covered = tuple(observed(t) for t in ranked if t in canonical)
    undefined = tuple(observed(t) for t in ranked if t not in canonical)
    measurable = {w for w in canonical if w not in stopwords}
    return Coverage(
        vocabulary=vocabulary.name,
        covered=covered,
        undefined=undefined,
        unused=tuple(sorted(w for w in measurable if w not in frequencies)),
        unmeasurable=tuple(sorted(w for w in canonical if w in stopwords)),
    )
