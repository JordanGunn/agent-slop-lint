"""Type-annotation extraction + escape-hatch density (Module measure).

Per-grammar tree-sitter queries (``type_annotation_queries``) run against a
module root via ``Node.query(..., capture="annotation")``; each captured
annotation is classified via ``is_dynamic_type``. Density = escape-hatch
annotations / total annotations over the module. The query goes through the AST
proxy — tree-sitter is no longer touched here.
"""
from __future__ import annotations

from typing import Any


def escape_hatch_counts(node: Any, grammar: Any) -> tuple[int, int]:
    """``(escape-hatch annotations, total annotations)`` over a module.

    The rule needs the raw total for its ``min_annotations`` noise floor — a bare
    density discards it, so a one-annotation module reads as 100% and false-fires.
    """
    queries = grammar.type_annotation_queries()
    if not queries:
        return (0, 0)
    total = escapes = 0
    for query_str, _kind in queries:
        for annotation in node.query(query_str, capture="annotation"):
            total += 1
            if grammar.is_dynamic_type(annotation.text):
                escapes += 1
    return (escapes, total)


def escape_hatch_density(node: Any, grammar: Any) -> float:
    """Fraction of a module's type annotations that use an escape-hatch type."""
    escapes, total = escape_hatch_counts(node, grammar)
    return escapes / total if total else 0.0
