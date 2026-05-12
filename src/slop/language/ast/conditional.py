"""``Conditional`` — if/elif/unless + ternary node types.

Covers every tree-sitter shape for branching-by-condition:
  - long-form if/elif/else (Python ``if_statement`` + ``elif_clause``,
    Ruby ``if`` + ``elsif``, Rust ``if_expression``, Julia
    ``if_statement`` + ``elseif_clause``)
  - modifier forms (Ruby ``if_modifier`` / ``unless_modifier``)
  - ternary / conditional expressions (Python ``conditional_expression``,
    most other grammars ``ternary_expression``, Ruby ``conditional``)
"""
from __future__ import annotations

from enum import StrEnum


class Conditional(StrEnum):
    IF_STATEMENT = "if_statement"
    IF_EXPRESSION = "if_expression"
    IF = "if"
    ELIF_CLAUSE = "elif_clause"
    ELSEIF_CLAUSE = "elseif_clause"
    ELSIF = "elsif"
    IF_MODIFIER = "if_modifier"
    UNLESS_MODIFIER = "unless_modifier"
    CONDITIONAL_EXPRESSION = "conditional_expression"
    TERNARY_EXPRESSION = "ternary_expression"
    CONDITIONAL = "conditional"
