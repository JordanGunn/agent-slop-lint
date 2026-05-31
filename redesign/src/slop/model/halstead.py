"""Halstead (1977) software-science measures for one callable.

Ported from the legacy halstead helper: walk the resolved body counting unique +
total operator/operand leaves (η1, η2, N1, N2), then derive the measures. Body-
local (skips nested callables). volume = N·log2(η) is the summable component;
difficulty/effort are non-additive.
"""
from __future__ import annotations

import math
from typing import Any

from ..component.metrics import HalsteadProfile
from .complexity import resolve_body


def counts(node: Any, content: bytes, grammar: Any) -> tuple[int, int, int, int]:
    """(η1, η2, N1, N2) — distinct/total operators and operands."""
    operator_set = grammar.operator_nodes()
    operand_set = grammar.operand_nodes()
    walk_from = resolve_body(node, grammar.definition_unwrap_types())
    nested = grammar.callable()
    operators: set[str] = set()
    operands: set[str] = set()
    n1_total = n2_total = 0
    stack = [walk_from]
    while stack:
        cur = stack.pop()
        ctype = cur.type
        if ctype in nested and cur is not walk_from:
            continue
        if cur.child_count == 0:
            text = content[cur.start_byte:cur.end_byte].decode("utf-8", errors="replace")
            if ctype in operator_set:
                operators.add(text); n1_total += 1
            elif ctype in operand_set:
                operands.add(text); n2_total += 1
        stack.extend(reversed(cur.children))
    return len(operators), len(operands), n1_total, n2_total


def profile(node: Any, content: bytes, grammar: Any) -> HalsteadProfile:
    """Full Halstead profile for one callable."""
    n1, n2, N1, N2 = counts(node, content, grammar)
    vocabulary = n1 + n2
    length = N1 + N2
    volume = length * math.log2(vocabulary) if vocabulary > 0 else 0.0
    difficulty = (n1 / 2) * (N2 / n2) if n2 > 0 else 0.0
    effort = difficulty * volume
    return HalsteadProfile(
        n1=n1, n2=n2, N1=N1, N2=N2, volume=volume, difficulty=difficulty, effort=effort,
    )


def volume(node: Any, content: bytes, grammar: Any) -> float:
    """Halstead volume only (the summable component)."""
    return profile(node, content, grammar).volume


def sloc(node: Any, content: bytes) -> int:
    """Physical source lines of a callable — non-blank lines in its span."""
    text = content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
    return sum(1 for line in text.splitlines() if line.strip())
