"""``Loop`` — for/while/do iteration node types.

Covers every tree-sitter loop shape: classic for-statement, for-in /
for-of / for-range / enhanced-for variants, while/do-while, plus
Ruby's ``until`` and modifier forms.
"""
from __future__ import annotations

from enum import StrEnum


class Loop(StrEnum):
    FOR_STATEMENT = "for_statement"
    FOR_EXPRESSION = "for_expression"
    FOR = "for"
    FOR_IN_STATEMENT = "for_in_statement"
    FOR_OF_STATEMENT = "for_of_statement"
    FOR_RANGE_LOOP = "for_range_loop"
    ENHANCED_FOR_STATEMENT = "enhanced_for_statement"
    FOREACH_STATEMENT = "foreach_statement"
    WHILE_STATEMENT = "while_statement"
    WHILE_EXPRESSION = "while_expression"
    WHILE = "while"
    WHILE_MODIFIER = "while_modifier"
    DO_STATEMENT = "do_statement"
    LOOP_EXPRESSION = "loop_expression"
    UNTIL = "until"
    UNTIL_MODIFIER = "until_modifier"
