"""Lexicon scaffolding (scratch).

See README.md for context. Public surface:

- ``Lexeme`` — one tokenised identifier
- ``Lexicon`` — bag of Lexemes with statistical queries
- ``UNIVERSAL_NOISE`` — Layer-1 ignore set (Newman 2017 + glue)
"""
from .lexeme import Lexeme
from .lexicon import Lexicon
from .words import UNIVERSAL_NOISE

__all__ = ["Lexeme", "Lexicon", "UNIVERSAL_NOISE"]
