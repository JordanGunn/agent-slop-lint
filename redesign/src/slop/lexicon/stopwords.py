"""Stop words — the curated, code-specific noise list stripped before measurement.

Two reasons this is hand-curated rather than a library list:

1. It is *code*, not prose. A generic English stop-word list (NLTK et al.) would
   suppress identifier-common words (``id``, ``index``, ``key``) only by accident and
   would miss the software-engineering boilerplate that actually drowns signal.
2. SE boilerplate is deliberately **not** noise here. ``manager`` / ``helper`` /
   ``handler`` carry the over-abstraction signal a future ``hammers``-style rule
   wants; stripping them would erase exactly what we measure.

``STOP_WORDS`` is the default; it is injectable — a :class:`~slop.lexicon.corpus.Lexicon`
takes a ``stopwords`` set, so a caller analysing a different vocabulary can substitute
its own without forking the kernel.
"""
from __future__ import annotations

# Newman et al. (SANER 2017): the 14 single-letter / ultra-generic tokens that
# carry no domain signal in identifiers.
_NEWMAN_14 = frozenset({
    "a", "length", "id", "pos", "start", "next", "str", "key",
    "f", "x", "index", "p", "left", "result",
})

# English glue that appears between meaningful tokens in multi-word identifiers.
_GLUE = frozenset({
    "the", "an", "is", "are", "to", "for", "in", "on", "of",
    "with", "by", "as", "at", "and", "or", "but", "if",
})

#: Default code stop-word set: Newman-14 + English glue.
STOP_WORDS = _NEWMAN_14 | _GLUE
