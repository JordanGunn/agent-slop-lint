"""The vocabulary boundary: what slop needs from a canonical vocabulary, whoever authors it.

A vocabulary is a set of named terms, each of a known kind, with the fields it is
declared to carry. slop reads it and never writes it: the vocabulary is authored and
governed elsewhere (today as an Open Ontology model, exported as JSON IR), and this
interface is the seam that keeps the rest of slop from depending on that tool.

Comparison form: a code identifier and a vocabulary term are the same word when their
case-folded word tokens agree, so ``Chunk``, ``chunk`` and ``CHUNK`` agree and so do
``escalate-ticket`` and ``escalate_ticket``. That is the whole matching rule; there is
no fuzzy match, because a near miss that is silently accepted is a missed finding.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from ..lexicon.tokenize import split_tokens


class TermKind(Enum):
    """What a canonical term names."""

    ENTITY = "entity"
    RELATION = "relation"
    ACTION = "action"
    QUERY = "query"


@dataclass(frozen=True)
class Term:
    """One canonical word: its name as declared, its kind, and what it is declared to carry.

    ``fields`` are field keys (``ticket/title``) for entities and relations, input names
    for actions. ``ends`` is the (from, to) entity pair of a relation, else None.
    ``description`` is the vocabulary's own definition of the word, None if it has none.
    """

    name: str
    kind: TermKind
    description: str | None
    fields: tuple[str, ...]
    ends: tuple[str, str] | None = None

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "description": self.description,
            "fields": list(self.fields),
            "ends": list(self.ends) if self.ends else None,
        }


def normalize(name: str) -> str:
    """The comparison form of an identifier or term name (see module docstring)."""
    return "".join(token.lower() for token in split_tokens(name.replace("-", "_")))


class Vocabulary(ABC):
    """A canonical vocabulary. Implementations only supply ``name`` and ``terms``."""

    @property
    @abstractmethod
    def name(self) -> str:
        """A label for reports: the model name and version, or a file name."""
        ...

    @abstractmethod
    def terms(self) -> Sequence[Term]:
        """Every term, in declaration order."""
        ...

    def entities(self) -> Sequence[Term]:
        """The terms that name things (the ones a class is expected to be called)."""
        return tuple(t for t in self.terms() if t.kind is TermKind.ENTITY)

    def term(self, name: str) -> Term | None:
        """The term ``name`` agrees with, entities first; None when it is not canonical."""
        wanted = normalize(name)
        order = {TermKind.ENTITY: 0, TermKind.RELATION: 1, TermKind.ACTION: 2, TermKind.QUERY: 3}
        agreeing = [t for t in self.terms() if normalize(t.name) == wanted]
        return min(agreeing, key=lambda t: order[t.kind]) if agreeing else None
