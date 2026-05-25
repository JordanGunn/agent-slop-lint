"""Lexical metric registry — assembles per-module ``RULE`` constants.

Each metric module owns its own ``RULE: RuleDefinition`` at module
bottom. This package's job is one-line: gather them all into
``LEXICAL_RULES``. To add a new metric, drop a new module here
exporting ``RULE`` and list it below.

Naming-discipline rules that ride on the ``Lexicon`` view. Each rule
points at structural debt expressed through naming.
"""
from __future__ import annotations

from slop.linter.types import RuleDefinition

from . import (
    confusion,
    cowards,
    hammers,
    imposters,
    slackers,
    sprawl,
    stutter,
    tautology,
    verbosity,
)

LEXICAL_RULES: list[RuleDefinition] = [
    stutter.RULE,
    verbosity.RULE,
    cowards.RULE,
    hammers.RULE,
    tautology.RULE,
    sprawl.RULE,
    imposters.RULE,
    slackers.RULE,
    confusion.RULE,
]
