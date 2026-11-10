"""Literals that are objectively worth naming.

An *objective* violation is one that follows from syntax and a stated limit alone, so no
idiom or intent can excuse it. A *subjective* one depends on what the author meant; it is
not measured here and never fails a lint run. Only two patterns are objective:

- a float with a fractional part (``9.81``, ``0.7``) used as an operand of an arithmetic,
  comparison, bitwise or logical operator (``x * 9.81``). Integers are never measured:
  ``3`` may be a dimension, an offset, a count or a magic number, and syntax cannot say.
  ``0.5`` and floats without a fractional part (``100.0``) are ordinary.
- a string of at least ``min_length`` characters that appears again and again in one
  module (the shape of Sonar S1192). Short strings (``'r'`` in ``mode='r'``), strings
  assigned directly to a name (the constant itself), fragments of ``+`` concatenation, and
  f-strings are not counted.

Do not grow this module with exemptions for idioms (masks, unit conversions, format
offsets). A case that needs an exemption is subjective: leave it to judgement.
"""
from __future__ import annotations

from typing import Any

from .records import LiteralUse

# Arithmetic, comparison, bitwise and logical operator tokens, with their augmented forms.
# Keywords (``return``, ``if``) and punctuation (``=>``, ``?``, ``...``) also appear in a
# grammar's operator set; a literal beside them is not an operand of an operation.
_OPERATIONS = frozenset({
    "+", "-", "*", "/", "%", "**", "//", "@",
    "<", ">", "<=", ">=", "==", "!=", "===", "!==", "<>",
    "<<", ">>", ">>>", "&", "|", "^", "&&", "||",
    "+=", "-=", "*=", "/=", "%=", "**=", "//=", "<<=", ">>=", ">>>=", "&=", "|=", "^=",
})
_ASSIGNMENT = frozenset({"=", ":="})
_QUOTES = "\"'`"


def magic_floats(module: Any) -> list[LiteralUse]:
    """Each distinct float operand in the module, at its first use, with its use count."""
    grammar = module._grammar
    literal_types = grammar.numeric_literal_nodes()
    operator_types = grammar.operator_nodes()
    uses: dict[str, LiteralUse] = {}
    for node in module._ast_node().walk():
        if node.type not in literal_types or not _is_magic_float(node.text):
            continue
        if not _operator_symbols(node.parent, operator_types) & _OPERATIONS:
            continue
        _record(uses, node)
    return list(uses.values())


def repeated_strings(module: Any, *, min_length: int) -> list[LiteralUse]:
    """Each distinct string of ``min_length`` or more characters, at its first use, with
    its use count. The caller decides how many uses are too many."""
    grammar = module._grammar
    string_types = grammar.string_literal_nodes()
    operator_types = grammar.operator_nodes()
    uses: dict[str, LiteralUse] = {}
    for node in module._ast_node().walk():
        if node.type not in string_types:
            continue
        text = node.text
        if "\n" in text or _is_interpolated(text) or len(_body(text)) < min_length:
            continue
        symbols = _operator_symbols(node.parent, operator_types)
        if symbols & _ASSIGNMENT or "+" in symbols:
            continue
        _record(uses, node)
    return list(uses.values())


def _operator_symbols(parent: Any, operator_types: frozenset[str]) -> set[str]:
    """The symbols of ``parent``'s operator tokens. A grammar may type every operator
    token alike (Julia: ``operator``) and put the symbol in the text."""
    if parent is None:
        return set()
    return {k.text for k in parent.children() if k.type in operator_types}


def _record(uses: dict[str, LiteralUse], node: Any) -> None:
    text = node.text
    first = uses.get(text)
    if first is None:
        line, column = node._raw.start_point[0] + 1, node._raw.start_point[1] + 1
        uses[text] = LiteralUse(value=text, line=line, column=column, count=1)
    else:
        uses[text] = LiteralUse(value=text, line=first.line, column=first.column, count=first.count + 1)


def _is_magic_float(text: str) -> bool:
    try:
        value = float(text.replace("_", "").lower().rstrip("fdl"))
    except ValueError:
        return False
    if value != value or value in (float("inf"), float("-inf")):
        return False
    return value != int(value) and value != 0.5


def _prefix(text: str) -> str:
    return text[:len(text) - len(text.lstrip("rbfuRBFU"))]


def _is_interpolated(text: str) -> bool:
    return "f" in _prefix(text).lower()


def _body(text: str) -> str:
    return text[len(_prefix(text)):].strip(_QUOTES)
