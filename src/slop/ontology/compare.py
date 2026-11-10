"""Compare the names observed in code against a canonical vocabulary.

Three facts, no judgment:

- ``matched``: a canonical entity and every observed class that agrees with it.
- ``unknown``: an observed class no canonical entity agrees with.
- ``unused``: a canonical entity no observed class agrees with.

A class is observed through :func:`slop.scope.find.find`; the agreement rule is
:func:`slop.ontology.interface.normalize`. Empty inputs raise instead of reporting a
clean comparison: with nothing observed, "no unknown names" would be a false pass.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..scope.find import Match
from .interface import Term, Vocabulary, normalize


@dataclass(frozen=True)
class Comparison:
    matched: tuple[tuple[Term, tuple[Match, ...]], ...]
    unknown: tuple[Match, ...]
    unused: tuple[Term, ...]

    def as_dict(self) -> dict:
        return {
            "matched": [{"term": t.name, "observed": [m.as_dict() for m in ms]} for t, ms in self.matched],
            "unknown": [m.as_dict() for m in self.unknown],
            "unused": [t.name for t in self.unused],
        }


def compare(observed: Sequence[Match], vocabulary: Vocabulary) -> Comparison:
    """Compare observed class matches with the vocabulary's entities."""
    entities = vocabulary.entities()
    if not entities:
        raise ValueError(f"{vocabulary.name} declares no entities to compare against")
    if not observed:
        raise ValueError("no classes were observed, so the comparison would be vacuous")

    by_form: dict[str, list[Match]] = {}
    for match in observed:
        by_form.setdefault(normalize(match.name), []).append(match)

    known = {normalize(t.name) for t in entities}
    matched = tuple(
        (t, tuple(by_form[normalize(t.name)])) for t in entities if normalize(t.name) in by_form
    )
    unused = tuple(t for t in entities if normalize(t.name) not in by_form)
    unknown = tuple(m for form, ms in sorted(by_form.items()) if form not in known for m in ms)
    return Comparison(matched=matched, unknown=unknown, unused=unused)
