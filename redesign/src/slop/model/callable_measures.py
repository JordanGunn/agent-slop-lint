"""Per-callable non-aggregatable measures: magic literals, parameter mutations,
sentinel parameters. Ported from the legacy magic_literals / hidden_mutators /
sentinels compute (trivial-value and sentinel-name constants preserved)."""
from __future__ import annotations

import re
from typing import Any

from ..component.metrics import MagicLiteral, ParameterMutation, SentinelParameter

_TRIVIAL_INTS: frozenset[int] = frozenset({-1, 0, 1, 2})
_TRIVIAL_FLOATS: frozenset[float] = frozenset({-1.0, 0.0, 0.5, 1.0, 2.0, 100.0})

SENTINEL_NAMES: frozenset[str] = frozenset({
    "status", "mode", "kind", "level", "format",
    "role", "action", "category", "severity", "phase",
    "stage", "style", "direction", "state", "type",
    "method", "strategy", "algorithm", "protocol",
    "encoding", "codec", "backend", "driver", "engine",
})
_STRIP_TRAILING = re.compile(r"_+$")


def magic_literals(node: Any, content: bytes, grammar: Any) -> list[MagicLiteral]:
    """Distinct non-trivial numeric literals in the callable body (excludes nested callables)."""
    literal_types = grammar.numeric_literal_nodes()
    if not literal_types:
        return []
    nested = grammar.callable()
    seen: dict[str, int] = {}
    stack = [node]
    while stack:
        cur = stack.pop()
        if cur.type in nested and cur is not node:
            continue
        if cur.type in literal_types:
            text = content[cur.start_byte:cur.end_byte].decode("utf-8", errors="replace")
            if text not in seen and not _is_trivial(text):
                seen[text] = cur.start_point[0] + 1
        stack.extend(cur.children)
    return [MagicLiteral(value=t, line=ln) for t, ln in seen.items()]


def mutated_parameters(node: Any, content: bytes, grammar: Any) -> list[ParameterMutation]:
    """Collection/reference parameters mutated in place (grammar-specific shapes)."""
    return [
        ParameterMutation(parameter=param, kind=method, line=line)
        for param, method, line in grammar.hidden_mutators(node, content, require_type_annotation=True)
    ]


def sentinel_parameters(node: Any, content: bytes, grammar: Any) -> list[SentinelParameter]:
    """String-typed parameters with sentinel names that should be Literal/Enum."""
    out: list[SentinelParameter] = []
    for name, annotated in grammar.stringly_typed_params(node, content):
        key = _STRIP_TRAILING.sub("", name).lower()
        if key not in SENTINEL_NAMES:
            continue
        if not annotated and grammar.id != "ruby":
            continue
        out.append(SentinelParameter(name=name, observed_literals=()))
    return out


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
