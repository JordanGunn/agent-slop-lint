"""Seed the vocabulary from the words the code declares.

Every word the code declares becomes a candidate term, without a definition, most used first
(then by the number of files it occurs in, then alphabetically), spelled the way the code
spells it most often. Terms already in the vocabulary are kept as they are, first and in their
order, and a word that already labels a term is not added again. Stop words, single letters and
numbers are not vocabulary. Agreeing which candidates are domain concepts, and what they mean,
is for people: the draft only makes sure no word the code uses is missing."""
from __future__ import annotations

from ..lexicon.corpus import Lexicon
from ..lexicon.stopwords import STOP_WORDS
from .model import Scheme, Term


def draft(lexicon: Lexicon, existing: Scheme | None, name: str) -> Scheme:
    """``existing`` with every word of ``lexicon`` it does not yet label added as an undefined
    term; a new scheme called ``name`` when there is none."""
    terms = list(existing.terms) if existing is not None else []
    known = existing.words(defined_only=False) if existing is not None else {}
    spellings = lexicon.spellings()

    for word in lexicon.ranked():
        if word in known or word in STOP_WORDS or len(word) < 2 or word.isdigit():
            continue
        terms.append(Term(pref_label=spellings.get(word, word)))
    return Scheme(existing.name if existing is not None else name, terms)
