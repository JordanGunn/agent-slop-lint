"""Halstead (1977) software-science measures for one callable.

Walk the resolved body counting unique + total operator/operand leaves
(η1, η2, N1, N2), then derive the measures. Runs on the ``slop.ast`` ``Node``
proxy (``node.body()`` + ``Node.walk(prune={CALLABLE})``); body-local, so it
skips nested callables. volume = N·log2(η) is the summable component;
difficulty/effort are non-additive.
"""
from __future__ import annotations

import math
from typing import Any

from ..ast import NodeKind
from ..component.metrics import HalsteadProfile


def counts(node: Any, grammar: Any) -> tuple[int, int, int, int]:
    """(η1, η2, N1, N2) — distinct/total operators and operands."""
    operator_set = grammar.operator_nodes()
    operand_set = grammar.operand_nodes()
    operators: set[str] = set()
    operands: set[str] = set()
    n1_total = n2_total = 0
    for n in node.body().walk(prune=frozenset({NodeKind.CALLABLE})):
        if n.child_count == 0:
            ntype = n.type
            if ntype in operator_set:
                operators.add(n.text); n1_total += 1
            elif ntype in operand_set:
                operands.add(n.text); n2_total += 1
    return len(operators), len(operands), n1_total, n2_total


def profile(node: Any, grammar: Any) -> HalsteadProfile:
    """Full Halstead profile for one callable."""
    n1, n2, N1, N2 = counts(node, grammar)
    vocabulary = n1 + n2
    length = N1 + N2
    volume = length * math.log2(vocabulary) if vocabulary > 0 else 0.0
    difficulty = (n1 / 2) * (N2 / n2) if n2 > 0 else 0.0
    effort = difficulty * volume
    return HalsteadProfile(
        n1=n1, n2=n2, N1=N1, N2=N2, volume=volume, difficulty=difficulty, effort=effort,
    )


def volume(node: Any, grammar: Any) -> float:
    """Halstead volume only (the summable component)."""
    return profile(node, grammar).volume


def sloc(node: Any) -> int:
    """Physical source lines of a callable — non-blank lines in its span."""
    return sum(1 for line in node.text.splitlines() if line.strip())
