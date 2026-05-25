"""Halstead vocabulary primitives — shared by volume + density metrics.

Both metrics need the (η₁, η₂, N₁, N₂) tuple per callable: the four
counts Halstead 1977 defines as the base for every derived measure.
``_halstead_for`` returns the tuple for one callable (or None if the
callable's language doesn't declare operator/operand node sets).
``_collect_tokens`` walks the body AST counting unique + total
operator and operand leaves, skipping into nested callables (each
gets its own metric).

``_slop`` builds the function-scope finding for a callable; volume
also uses the shared class-scope ``_slop`` from ``_class_index`` for
its class-scope aggregation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING

from slop.language.grammars import LANGUAGE_BY_ID
from slop.linter.slop import Slop

if TYPE_CHECKING:
    from slop.structure.view import Structure


def _halstead_for(
    structure: Structure, c: Any,
) -> tuple[int, int, int, int] | None:
    """Compute (η₁, η₂, N₁, N₂) for one callable. None if not computable."""
    from slop.structure.view import _resolve_body

    language_id = structure.language_for(c)
    if language_id is None:
        return None
    lang = LANGUAGE_BY_ID.get(language_id)
    if lang is None:
        return None
    operator_set = lang.operator_nodes()
    operand_set = lang.operand_nodes()
    if not operator_set and not operand_set:
        return None
    node = structure._node_by_key.get((str(c.path), c.qualname))  # noqa: SLF001
    content = structure._content_by_key.get((str(c.path), c.qualname))  # noqa: SLF001
    if node is None or content is None:
        return None
    walk_from = _resolve_body(node, lang.definition_unwrap_types())
    nested_callables = lang.callable()
    return _collect_tokens(walk_from, content, operator_set, operand_set, nested_callables)


def _collect_tokens(
    root_node: Any,
    content: bytes,
    operator_set: frozenset[str],
    operand_set: frozenset[str],
    nested_callables: frozenset[str],
) -> tuple[int, int, int, int]:
    """Walk ``root_node``, count unique + total operator/operand leaves."""
    operators: set[str] = set()
    operands: set[str] = set()
    total_n1 = 0
    total_n2 = 0

    stack: list[Any] = [root_node]
    while stack:
        cur = stack.pop()
        ctype = cur.type
        if ctype in nested_callables and cur is not root_node:
            continue
        if cur.child_count == 0:
            if ctype in operator_set:
                text = content[cur.start_byte:cur.end_byte].decode("utf-8", errors="replace")
                operators.add(text)
                total_n1 += 1
            elif ctype in operand_set:
                text = content[cur.start_byte:cur.end_byte].decode("utf-8", errors="replace")
                operands.add(text)
                total_n2 += 1
        for child in reversed(cur.children):
            stack.append(child)

    return len(operators), len(operands), total_n1, total_n2


def _slop(
    rule: str,
    c: Any,
    root: Path,
    severity: str,
    value: float,
    threshold: float,
    message: str,
    extra: dict | None = None,
) -> Slop:
    """Build a function-scope Slop for a Halstead finding."""
    try:
        rel = str(c.path.relative_to(root))
    except ValueError:
        rel = str(c.path)
    metadata: dict[str, Any] = {"end_line": c.end_line, "qualname": c.qualname}
    if extra:
        metadata.update(extra)
    return Slop(
        rule=rule,
        file=rel,
        line=c.line,
        symbol=c.qualname.split(".")[-1],
        message=message,
        severity=severity,
        value=value,
        threshold=threshold,
        metadata=metadata,
    )
