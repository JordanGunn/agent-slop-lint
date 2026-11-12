"""The project's vocabulary: terms, what they mean, and how they relate (W3C SKOS).

A ``Term`` is one concept named by a single word. It carries the SKOS lexical labels, a
``prefLabel`` (the word to use), ``altLabel`` (other accepted words: synonyms, acronyms) and
``hiddenLabel`` (words to recognise but never use: retired names, misspellings), plus a
``definition`` and links to ``broader`` and ``related`` terms by their preferred labels.

A term is *defined* when it has a definition. Only defined terms bind the code: an undefined
term is a draft candidate, a word the code uses that nobody has given a meaning yet.

Words compare by stem, as the lexicon counts them (``slop.lexicon.inflection``): ``Laz``, ``LAZ``
and ``laz`` are one word, and so are ``Node`` and ``nodes``.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..lexicon.inflection import stem


@dataclass(frozen=True)
class Term:
    pref_label: str
    definition: str | None = None
    alt_labels: tuple[str, ...] = ()
    hidden_labels: tuple[str, ...] = ()
    broader: tuple[str, ...] = ()
    related: tuple[str, ...] = ()

    @property
    def defined(self) -> bool:
        return bool(self.definition and self.definition.strip())

    def labels(self) -> tuple[str, ...]:
        """Every word that names this term, the preferred one first."""
        return (self.pref_label, *self.alt_labels, *self.hidden_labels)


class Scheme:
    """A named set of terms; implements ``slop.lexicon.vocabulary.Vocabulary``."""

    def __init__(self, name: str, terms: Iterable[Term]) -> None:
        self.name = name
        self.terms: tuple[Term, ...] = tuple(terms)
        self._by_word: dict[str, Term] = {}
        for term in self.terms:
            for label in term.labels():
                self._by_word.setdefault(stem(label), term)

    def term(self, word: str) -> Term | None:
        """The term any of whose labels is ``word``, or None."""
        return self._by_word.get(stem(word))

    def preferred(self, word: str) -> str | None:
        """The preferred label of the defined term that lists ``word`` as an alternative or
        hidden label; None when ``word`` is a preferred label or names no defined term."""
        term = self.term(word)
        if term is None or not term.defined or stem(term.pref_label) == stem(word):
            return None
        return term.pref_label

    def defined(self) -> tuple[Term, ...]:
        return tuple(t for t in self.terms if t.defined)

    def narrower(self, label: str) -> tuple[Term, ...]:
        """The terms whose ``broader`` names ``label``."""
        wanted = stem(label)
        return tuple(t for t in self.terms if any(stem(b) == wanted for b in t.broader))

    def words(self, *, defined_only: bool = True) -> dict[str, Term]:
        """Every label, by stem, mapped to its term."""
        return {w: t for w, t in self._by_word.items() if t.defined or not defined_only}
