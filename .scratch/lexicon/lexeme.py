"""Lexeme — one tokenised identifier.

A Lexeme is the smallest unit of slop's lexical analysis: a single
named symbol, decomposed into its word-tokens once at construction
time. Frozen and hashable so it can be shared freely across any
number of Lexicons without retokenisation cost.
"""
from __future__ import annotations

from dataclasses import dataclass

from ._naming import split_identifier


@dataclass(frozen=True, slots=True)
class Lexeme:
    """One tokenised identifier.

    ``text`` is the source-form (e.g. ``"get_user_email"``).
    ``tokens`` is the snake/Camel-split sequence in original case.
    ``lower`` is the same sequence case-folded. ``file`` and
    ``line`` are optional metadata for callers that need to
    surface findings against the original code location.
    """

    text: str
    tokens: tuple[str, ...]
    lower: tuple[str, ...]
    file: str | None = None
    line: int | None = None

    @classmethod
    def of(
        cls,
        text: str,
        *,
        file: str | None = None,
        line: int | None = None,
    ) -> "Lexeme":
        """Build a Lexeme by tokenising ``text`` once."""
        toks = tuple(split_identifier(text))
        return cls(
            text=text,
            tokens=toks,
            lower=tuple(t.lower() for t in toks),
            file=file,
            line=line,
        )
