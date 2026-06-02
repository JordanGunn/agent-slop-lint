"""slop.lexicon — the linguistic kernel.

A self-contained vocabulary-analysis library over a corpus of identifier tokens. It
tokenises, counts, measures distribution, and (as it grows) clusters — in the
vocabulary of lexicography, not of slop. The governing test for every member: *would
a corpus linguist recognise this concept independent of slop?* Hapax ratio,
type/token counts, frequency, Zipf shape, collocations, formal concepts,
edit-distance clustering — yes. "imposters", "sprawl", threshold verdicts — no; those
are slop-invented and live in the rule layer above.

The hard boundary: ``slop.lexicon`` is importable and usable **outside the linter**.
It depends only on ``slop.span`` (the shared source-location primitive) and the
standard library — never on ``component``, ``rules``, or ``linter``. It is a peer of
``slop.ast``, not a dependent: ``ast`` yields identifiers *as written*; the lexicon
decides what counts as vocabulary.

Current surface (consumer-driven; grows as rules need it):
``Role``, ``Lexeme``, ``Lexicon``, ``split_tokens``, ``STOP_WORDS``.
"""
from __future__ import annotations

from .corpus import Lexicon
from .distribution import (
    HAPAX_RATIO_NORM,
    ZIPF_ALPHA_NORM,
    ZIPF_R2_NORM,
    TokenDistribution,
    token_distribution,
)
from .roles import Role
from .stopwords import STOP_WORDS
from .tokenize import Lexeme, split_tokens

__all__ = [
    "Role",
    "Lexeme",
    "Lexicon",
    "split_tokens",
    "STOP_WORDS",
    "TokenDistribution",
    "token_distribution",
    "ZIPF_ALPHA_NORM",
    "ZIPF_R2_NORM",
    "HAPAX_RATIO_NORM",
]
