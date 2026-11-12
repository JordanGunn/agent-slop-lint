"""Observed vocabulary against a canonical vocabulary, at the level of word tokens.

This compares the *words* the code declares (class, function, parameter, property and
module names, split into words) with the words the project's vocabulary defines: the
labels of its defined terms. Four facts, none of them a judgment:

Words are matched by stem (``slop.lexicon.inflection``) and shown as the code spells them, or
for canonical words, as the vocabulary does.

- ``covered``: observed tokens the vocabulary defines.
- ``undefined``: observed tokens it does not define, most used first. This is the list
  that shows vocabulary the ontology has not named yet.
- ``unused``: canonical tokens the code never uses.
- ``unmeasurable``: canonical tokens the Lexicon's noise list strips before measurement
  (``key``, ``index``, ``result`` ...). They can never be observed, so reporting them
  as unused would be wrong.

There are no thresholds here. ``undefined`` is ordered, not filtered; how long a prefix
of it matters is the reader's call. An undefined term (a draft candidate) defines nothing,
and definitions are prose, not tokenised.
"""
from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from ..lexicon import STOP_WORDS, Lexicon, stem
from ..ontology import Scheme


@dataclass(frozen=True)
class Observed:
    """One token as the code uses it: how often, and in how many files."""

    token: str
    count: int
    files: int
    defined_by: tuple[str, ...] = ()   # the defined term this word names, if any

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


def canonical_tokens(scheme: Scheme) -> dict[str, tuple[str, ...]]:
    """The stem of each word a defined term is labelled with -> that term's preferred label."""
    return {word: (term.pref_label,) for word, term in sorted(scheme.words().items())}


def _labels(scheme: Scheme) -> dict[str, str]:
    """The stem of each label of a defined term -> the label as the vocabulary writes it."""
    return {stem(label): label for term in scheme.defined() for label in term.labels()}


def coverage(lexicon: Lexicon, vocabulary: Scheme, *,
             stopwords: Collection[str] = STOP_WORDS) -> Coverage:
    """Compare ``lexicon`` (observed) with ``vocabulary`` (canonical).

    Raises when nothing was observed: with no tokens, "everything is covered" and
    "nothing is undefined" would both be vacuously true."""
    frequencies = lexicon.frequencies()
    if not frequencies:
        raise ValueError("no identifier tokens were observed, so the comparison would be vacuous")
    canonical = canonical_tokens(vocabulary)
    if not canonical:
        raise ValueError(f"{vocabulary.name} defines no words yet: give its terms definitions")
    spread, spellings, labels = lexicon.spread(), lexicon.spellings(), _labels(vocabulary)

    def observed(token: str) -> Observed:
        return Observed(spellings.get(token, token), frequencies[token], spread.get(token, 0), canonical.get(token, ()))

    ranked = lexicon.ranked()
    covered = tuple(observed(t) for t in ranked if t in canonical)
    undefined = tuple(observed(t) for t in ranked if t not in canonical)
    stopped = {w for w in canonical if labels[w].lower() in stopwords}
    return Coverage(
        vocabulary=vocabulary.name,
        covered=covered,
        undefined=undefined,
        unused=tuple(sorted(labels[w] for w in canonical if w not in stopped and w not in frequencies)),
        unmeasurable=tuple(sorted(labels[w] for w in stopped)),
    )
