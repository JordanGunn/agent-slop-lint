"""Module-level ignore-list constants.

Layered ignore model per ``docs/research/identifier-vocabulary.md``:

- Layer 1 — universal noise (cross-corpus universal identifiers
  + identifier glue words). Shipped here as ``UNIVERSAL_NOISE``.
- Layer 2 — SE boilerplate (``manager``, ``helper``, ``service``).
  Deliberately NOT included; that vocabulary is the signal
  ``lexical.hammers`` exists to detect.
- Layer 4 — per-language ecosystem idioms (``ctx``/``err`` Go,
  ``ptr``/``buf`` C/C++, etc.). Deferred to ``docs/backlog/09.md``.
- Layer 5 — corpus-derived TF-IDF / Poisson noise. Deferred until
  Phase 06 fixture corpora exist.

Lexicon does NOT apply any of these by default; callers opt in
per-query via the ``exclude=`` argument on Lexicon methods.
"""
from __future__ import annotations


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
# Curated from common usage; not literature-grounded but a small,
# uncontroversial set.
_GLUE: frozenset[str] = frozenset({
    "the", "an", "is", "are", "to", "for", "in", "on", "of",
    "with", "by", "as", "at", "and", "or", "but", "if",
})


UNIVERSAL_NOISE: frozenset[str] = _NEWMAN_14 | _GLUE
"""The only ignore set shipped in v1. Layer 1 + Layer 3 of the
layered ignore model; safe default for callers that want a
literature-grounded floor."""
