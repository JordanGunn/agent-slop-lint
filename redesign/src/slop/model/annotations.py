"""Type-annotation extraction + escape-hatch density (Module measure).

Ported from the legacy ``structure/annotations.py``: per-grammar tree-sitter
queries (``type_annotation_queries``) run against a module root; each captured
annotation is classified via ``is_dynamic_type``. Density = escape-hatch
annotations / total annotations over the module's extent.
"""
from __future__ import annotations

from typing import Any


def escape_hatch_density(root_node: Any, content: bytes, grammar: Any) -> float:
    """Fraction of a module's type annotations that use an escape-hatch type."""
    queries = grammar.type_annotation_queries()
    if not queries or root_node is None:
        return 0.0
    ts_lang = grammar.ts_language()
    if ts_lang is None:
        return 0.0
    total = escapes = 0
    for query_str, _kind in queries:
        for node in _annotation_nodes(ts_lang, query_str, root_node):
            text = content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            total += 1
            if grammar.is_dynamic_type(text):
                escapes += 1
    return escapes / total if total else 0.0


def _annotation_nodes(ts_lang: Any, query_str: str, root_node: Any):
    """Yield nodes captured as ``@annotation`` (modern Query/QueryCursor or legacy API)."""
    import tree_sitter

    query_cls = getattr(tree_sitter, "Query", None)
    cursor_cls = getattr(tree_sitter, "QueryCursor", None)
    if query_cls is not None and cursor_cls is not None:
        cursor = cursor_cls(query_cls(ts_lang, query_str))
        for _idx, captures in cursor.matches(root_node):
            yield from _from_captures(captures)
        return
    query = ts_lang.query(query_str)
    for match in query.matches(root_node):
        if isinstance(match, tuple) and len(match) == 2:
            yield from _from_captures(match[1])


def _from_captures(captures):
    if isinstance(captures, dict):
        yield from captures.get("annotation", [])
        return
    for name, node in captures:
        if name == "annotation":
            yield node
