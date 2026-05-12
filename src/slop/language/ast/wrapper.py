"""``Wrapper`` — tree-sitter node types that wrap a definition or its name.

Includes C++ ``template_declaration`` (wraps a function/class), Julia's
``signature → call_expression`` chain (wraps a function name), and the
C/C++ declarator chain (``function_declarator`` / ``pointer_declarator``
/ ``reference_declarator`` / ``parenthesized_declarator``) that wraps
the identifier in C-family function definitions.

These are the nodes a walker descends THROUGH (rather than counting or
treating as a leaf) to reach the actual definition or name.
"""
from __future__ import annotations

from enum import StrEnum


class Wrapper(StrEnum):
    TEMPLATE_DECLARATION = "template_declaration"
    SIGNATURE = "signature"
    CALL_EXPRESSION = "call_expression"
    FUNCTION_DECLARATOR = "function_declarator"
    POINTER_DECLARATOR = "pointer_declarator"
    REFERENCE_DECLARATOR = "reference_declarator"
    PARENTHESIZED_DECLARATOR = "parenthesized_declarator"
