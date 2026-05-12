"""``Switch`` — switch/match/select multi-way branching node types.

Container shapes (``switch_statement``, ``match_expression``,
``select_statement``) and case shapes (``switch_case``, ``case_clause``,
``match_arm``, ``when``). Go's typed switches and select-statement
shapes (``expression_switch_statement`` / ``type_switch_statement`` /
``communication_case``) belong here.

The user's note: this enum includes ``match_*`` and ``select_*`` even
though the umbrella term is "Switch" — they're all forms of multi-way
branching that grammars treat similarly.
"""
from __future__ import annotations

from enum import StrEnum


class Switch(StrEnum):
    SWITCH_STATEMENT = "switch_statement"
    SWITCH_EXPRESSION = "switch_expression"
    SWITCH_CASE = "switch_case"
    SWITCH_LABEL = "switch_label"
    SWITCH_RULE = "switch_rule"
    SWITCH_SECTION = "switch_section"
    CASE_CLAUSE = "case_clause"
    CASE_STATEMENT = "case_statement"
    CASE = "case"
    WHEN = "when"
    MATCH_STATEMENT = "match_statement"
    MATCH_EXPRESSION = "match_expression"
    MATCH_ARM = "match_arm"
    EXPRESSION_SWITCH_STATEMENT = "expression_switch_statement"
    EXPRESSION_CASE = "expression_case"
    TYPE_SWITCH_STATEMENT = "type_switch_statement"
    TYPE_CASE = "type_case"
    SELECT_STATEMENT = "select_statement"
    COMMUNICATION_CASE = "communication_case"
