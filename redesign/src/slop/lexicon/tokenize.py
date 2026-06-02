"""Tokenisation — splitting an identifier *as written* into word tokens.

The lexicon's first act on each unit. The tokenizer is **convention-blind**: it
splits camelCase, snake_case, PascalCase, acronym runs (``HTTPServer`` ->
``HTTP``/``Server``), and digit boundaries uniformly, with no knowledge of what
casing convention an identifier "should" follow. Case is preserved through
``split_tokens`` and normalised away later, at :class:`~slop.lexicon.corpus.Lexicon`
construction — so the kernel needs no ``Case`` enum and must not bind to a language's
declared convention (developers violate them: camelCase in Python, PascalCase
fields). Casing-*convention* violation is a style signal, not structural debt, and is
a deliberate non-goal here.

This is where ``ast`` hands off: ``ast`` yields the identifier as written; deciding
what counts as vocabulary begins with this split.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..span import Span
from .roles import Role

_CAMEL_LOWER_UPPER = re.compile(r"([a-z])([A-Z])")
_CAMEL_UPPER_TITLE = re.compile(r"([A-Z]+)([A-Z][a-z])")


def split_tokens(name: str) -> tuple[str, ...]:
    """Split an identifier into word tokens (snake_case + CamelCase aware)."""
    cleaned = name.strip("_")
    cleaned = _CAMEL_LOWER_UPPER.sub(r"\1_\2", cleaned)
    cleaned = _CAMEL_UPPER_TITLE.sub(r"\1_\2", cleaned)
    return tuple(p for p in re.split(r"[_\d]+", cleaned) if p)


@dataclass(frozen=True)
class Lexeme:
    """One tokenised identifier with its provenance.

    ``text`` is the identifier as written; ``tokens`` is the case-preserving split;
    ``lower`` is the lowercased split (the form measurement uses). ``role`` and
    ``span`` are the provenance — the span doubles as the cross-view join key when a
    rule correlates a lexical finding with a structural one.
    """

    text: str
    tokens: tuple[str, ...]
    lower: tuple[str, ...]
    role: Role
    span: Span

    @classmethod
    def of(cls, text: str, *, role: Role, span: Span) -> "Lexeme":
        """Tokenise ``text`` once and capture its provenance."""
        toks = split_tokens(text)
        return cls(
            text=text,
            tokens=toks,
            lower=tuple(t.lower() for t in toks),
            role=role,
            span=span,
        )
