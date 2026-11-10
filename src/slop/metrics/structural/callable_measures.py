"""Magic literals: numeric literals that appear as operands of an operator in a callable.

A magic number is a numeric literal whose meaning the reader must guess (Martin, Clean
Code, 2008, G25; Fowler, Refactoring, 1999). Slop reads one syntactic context as the
signal: the literal is an operand of an arithmetic, comparison, bitwise or logical operator, as in
``x > 15`` or ``x * 86400``. A literal in a default value, a keyword argument, an index, a
call argument or the right side of ``name = 30`` is named by its position and is not
reported. That is a deliberate undercount: a bare call argument such as ``sleep(5)`` is
missed.

Ordinary values 0, 1 and 2 are never reported. Text that is not a number (a grammar can
name a type keyword like a numeric literal) is not reported either.
"""
from __future__ import annotations

from typing import Any

from ...ast import NodeKind
from .records import MagicLiteral

_ORDINARY = frozenset({0, 1, 2})
# Arithmetic, comparison, bitwise and logical operator tokens, with their augmented forms.
# Keywords (``return``, ``if``) and punctuation (``=>``, ``?``, ``...``) also appear in a
# grammar's operator set; a literal beside them is not an operand of an operation.
_OPERATIONS = frozenset({
    "+", "-", "*", "/", "%", "**", "//", "@",
    "<", ">", "<=", ">=", "==", "!=", "===", "!==", "<>",
    "<<", ">>", ">>>", "&", "|", "^", "&&", "||",
    "+=", "-=", "*=", "/=", "%=", "**=", "//=", "<<=", ">>=", ">>>=", "&=", "|=", "^=",
})


def magic_literals(node: Any, grammar: Any) -> list[MagicLiteral]:
    """Distinct magic numeric literals in the callable body (nested callables excluded),
    each at its first line."""
    literal_types = grammar.numeric_literal_nodes()
    operators = grammar.operator_nodes() & _OPERATIONS
    if not literal_types:
        return []
    seen: dict[str, int] = {}
    for cur in node.walk(prune=frozenset({NodeKind.CALLABLE})):
        if cur.type not in literal_types or cur.text in seen:
            continue
        value = _parse_numeric(cur.text)
        if value is None or value in _ORDINARY:
            continue
        parent = cur.parent
        if parent is not None and any(k.type in operators for k in parent.children()):
            seen[cur.text] = cur.line
    return [MagicLiteral(value=t, line=ln) for t, ln in seen.items()]


def _parse_numeric(text: str) -> int | float | None:
    stripped = text.replace("_", "").strip()
    if not stripped:
        return None
    while stripped and stripped[-1].isalpha() and not stripped.lower().startswith(("0x", "0b", "0o")):
        stripped = stripped[:-1]
    if stripped.endswith(("i", "j")):
        stripped = stripped[:-1]
    if not stripped:
        return None
    try:
        if stripped.startswith(("0x", "0X")):
            return int(stripped, 16)
        if stripped.startswith(("0b", "0B")):
            return int(stripped, 2)
        if stripped.startswith(("0o", "0O")):
            return int(stripped, 8)
        if "." in stripped or "e" in stripped or "E" in stripped:
            return float(stripped)
        return int(stripped)
    except ValueError:
        return None
