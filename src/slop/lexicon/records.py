"""Result records returned by ``Lexicon`` view methods.

Lexical rules read these read-only — the view owns the compute, the
record carries pure data.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NamedEntity:
    """One named callable or class-like scope, token-split.

    Consumed by lexical rules that reason about entity names
    (verbosity, stutter, cowards, hammers, tautology). ``tokens`` is
    the snake/Camel-split word list; the rule applies its own
    threshold logic on top.
    """

    name: str
    kind: str            # "function" | "class"
    file: str
    line: int
    language: str
    tokens: tuple[str, ...]
