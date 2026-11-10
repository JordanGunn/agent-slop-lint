"""Per-callable non-aggregatable measure: magic literals (distinct non-trivial numeric
literals in a body; trivial values are preserved from the legacy compute). No rule consumes
it yet; it awaits the structural-analysis layer."""
from __future__ import annotations

from typing import Any

from ...ast import NodeKind
from .records import MagicLiteral

_TRIVIAL_INTS: frozenset[int] = frozenset({-1, 0, 1, 2})
_TRIVIAL_FLOATS: frozenset[float] = frozenset({-1.0, 0.0, 0.5, 1.0, 2.0, 100.0})


def magic_literals(node: Any, grammar: Any) -> list[MagicLiteral]:
    """Distinct non-trivial numeric literals in the callable body (excludes nested callables).

    ``node`` is a ``slop.ast.Node``; ``Node.walk(prune={CALLABLE})`` is the
    body-local DFS that does not cross nested callables.
    """
    literal_types = grammar.numeric_literal_nodes()
    if not literal_types:
        return []
    seen: dict[str, int] = {}
    for cur in node.walk(prune=frozenset({NodeKind.CALLABLE})):
        if cur.type in literal_types:
            text = cur.text
            if text not in seen and not _is_trivial(text):
                seen[text] = cur.line
    return [MagicLiteral(value=t, line=ln) for t, ln in seen.items()]


def _is_trivial(text: str) -> bool:
    value = _parse_numeric(text)
    if value is None:
        return False
    return value in _TRIVIAL_INTS if isinstance(value, int) else value in _TRIVIAL_FLOATS


def _parse_numeric(text: str) -> int | float | None:
    stripped = text.replace("_", "").strip()
    if not stripped:
        return None
    while stripped and stripped[-1].isalpha():
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
