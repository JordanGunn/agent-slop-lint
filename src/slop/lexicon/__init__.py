"""slop.lexicon: the words in identifiers.

Splits identifiers into words, counts them by stem, and measures the distribution of the
counts (type and token counts, hapax ratio, Zipf exponent and fit): descriptive
lexicostatistics a corpus linguist would recognise. It sets no limits; rules do.

It depends only on ``slop.span`` and the standard library, never on ``scope``, ``rules`` or
``cli``, so it is usable outside the linter. ``ast`` yields identifiers as written; the lexicon
decides what counts as a word.

Surface: ``Role``, ``Lexeme``, ``Lexicon``, ``split_tokens``, ``stem``, ``plural``,
``STOP_WORDS``, ``Vocabulary``, ``TokenDistribution``, ``token_distribution``.
"""
from __future__ import annotations

from .corpus import Lexicon
from .inflection import plural, stem
from .distribution import (
    TokenDistribution,
    token_distribution,
)
from .roles import Role
from .stopwords import STOP_WORDS
from .tokenize import Lexeme, split_tokens
from .vocabulary import Vocabulary

__all__ = [
    "Role",
    "Lexeme",
    "Lexicon",
    "split_tokens",
    "stem",
    "plural",
    "STOP_WORDS",
    "Vocabulary",
    "TokenDistribution",
    "token_distribution",
]
