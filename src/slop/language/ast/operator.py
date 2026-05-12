"""``Operator`` — tree-sitter node types that host operator expressions.

Currently scoped to short-circuit boolean operators (Python's dedicated
``boolean_operator`` node, the C-family ``binary_expression`` with
``&&``/``||``/``??``, Ruby's ``binary``). These are the nodes that
cyclomatic / cognitive complexity walkers inspect for short-circuit
operator counting.

Distinct from ``Conditional`` because operators are expression-level
constructs, not statement-level decisions. Has room to grow if future
metrics need other operator-bearing node types.
"""
from __future__ import annotations

from enum import StrEnum


class Operator(StrEnum):
    BOOLEAN_OPERATOR = "boolean_operator"
    BINARY_EXPRESSION = "binary_expression"
    BINARY = "binary"
