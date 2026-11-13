"""Halstead (1977) volume of one callable.

Counts distinct and total operators and operands (η1, η2, N1, N2) over the callable's body,
skipping nested callables, and derives volume = N·log2(η).
"""
from __future__ import annotations

import math
from typing import Any

from ...ast import NodeKind


def counts(node: Any, grammar: Any) -> tuple[int, int, int, int]:
    """(η1, η2, N1, N2): distinct/total operators and operands.

    An operand is counted at its outermost node and its children are not visited, so a
    string literal is one operand however the grammar splits it into tokens (a Python
    ``string`` has ``string_start``/``string_content`` children). Names inside an
    interpolated string are therefore not counted separately."""
    operator_set = grammar.operator_nodes()
    operand_set = grammar.operand_nodes()
    operators: set[str] = set()
    operands: set[str] = set()
    n1_total = n2_total = 0
    body = node.body()
    stack = [body]
    while stack:
        n = stack.pop()
        if n.type in operand_set:
            operands.add(n.text)
            n2_total += 1
        elif n.child_count == 0:
            if n.type in operator_set:
                operators.add(n.text)
                n1_total += 1
        elif n is body or n.kind != NodeKind.CALLABLE:
            stack.extend(reversed(n.children()))
    return len(operators), len(operands), n1_total, n2_total


def volume(node: Any, grammar: Any) -> float:
    """Halstead volume of one callable: length times log2 of vocabulary, 0 for an empty body."""
    n1, n2, N1, N2 = counts(node, grammar)
    vocabulary = n1 + n2
    return (N1 + N2) * math.log2(vocabulary) if vocabulary > 0 else 0.0
