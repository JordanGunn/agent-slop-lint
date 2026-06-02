"""Per-callable non-aggregatable measures: magic literals, parameter mutations,
sentinel parameters. Ported from the legacy magic_literals / parameter_mutations /
sentinels compute (trivial-value and sentinel-name constants preserved)."""
from __future__ import annotations

import re
from typing import Any

from ..ast import NodeKind
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


def mutated_parameters(node: Any, content: bytes, grammar: Any) -> list[ParameterMutation]:
    """Parameters mutated in place. The grammar reports the in-place mutation facts
    (language-specific AST shapes); this maps them to ParameterMutation records."""
    return [
        ParameterMutation(parameter=param, kind=method, line=line)
        for param, method, line in grammar.parameter_mutations(node, content)
    ]


def sentinel_parameters(node: Any, content: bytes, grammar: Any) -> list[SentinelParameter]:
    """Sentinel-named string parameters that should be a Literal/Enum.

    The grammar reports the *fact* (each param's name + whether it is string-typed);
    the sentinel judgment (the SENTINEL_NAMES vocabulary, and that an annotation-less
    language like Ruby is flagged by name alone) is this rule's policy."""
    out: list[SentinelParameter] = []
    for name, is_string_typed in grammar.string_annotated_parameters(node, content):
        key = _STRIP_TRAILING.sub("", name).lower()
        if key not in SENTINEL_NAMES:
            continue
        if not is_string_typed and grammar.id != "ruby":
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
