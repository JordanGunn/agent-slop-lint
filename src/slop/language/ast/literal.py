"""``Literal`` — tree-sitter node types for numeric literal values.

Each grammar has its own conventions for naming numeric literals:
Python uses ``integer`` / ``float``; Go uses ``int_literal`` /
``float_literal`` plus ``imaginary_literal`` and ``rune_literal``;
Java uses ``decimal_integer_literal`` and friends; Ruby includes
``complex`` and ``rational``. This enum collects every numeric
literal node type any v2 grammar references.

Per-grammar selection lives on the grammar via ``numeric_literal_nodes()``.
Future expansion (string literals, boolean literals) would extend
this enum or split into ``NumericLiteral`` / ``StringLiteral`` if the
surface grows.
"""
from __future__ import annotations

from enum import StrEnum


class Literal(StrEnum):
    # Generic numeric (JS/TS)
    NUMBER = "number"
    # Python / Ruby
    INTEGER = "integer"
    FLOAT = "float"
    COMPLEX = "complex"
    RATIONAL = "rational"
    # Go
    INT_LITERAL = "int_literal"
    FLOAT_LITERAL = "float_literal"
    IMAGINARY_LITERAL = "imaginary_literal"
    RUNE_LITERAL = "rune_literal"
    # Rust / Julia / C#
    INTEGER_LITERAL = "integer_literal"
    REAL_LITERAL = "real_literal"
    # Java
    DECIMAL_INTEGER_LITERAL = "decimal_integer_literal"
    DECIMAL_FLOATING_POINT_LITERAL = "decimal_floating_point_literal"
    HEX_INTEGER_LITERAL = "hex_integer_literal"
    OCTAL_INTEGER_LITERAL = "octal_integer_literal"
    # C / C++
    NUMBER_LITERAL = "number_literal"
