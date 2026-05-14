"""Type-annotation extraction — feeds ``structural.types.escape_hatches``.

Substrate-aligned replacement for the regex-based legacy
``any_type_density_kernel``: per-grammar tree-sitter queries declared
on ``Language.type_annotation_queries`` run against each parsed file's
root, yielding ``(file, text, line, is_escape)`` records. The
escape-hatch classification is delegated to each grammar's
``is_escape_hatch_text`` predicate.

Coverage: Python, TypeScript, Go, Rust, Java, C#, Julia. JavaScript,
C, C++, and Ruby contribute nothing — JS lacks AST type annotations
(JSDoc is comment-level), C/C++ encode types in declarations (not
annotation nodes), Ruby is dynamically typed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slop.structure.view import Structure


@dataclass(frozen=True)
class TypeAnnotation:
    file: str
    text: str
    line: int
    kind: str           # "param" | "return" | "annotation" (grammar-specific)
    is_escape: bool


def extract_annotations(structure: Structure) -> list[TypeAnnotation]:
    """Run each grammar's annotation queries against its parsed trees."""
    from slop.language.grammars import LANGUAGE_BY_ID

    out: list[TypeAnnotation] = []
    for parse in structure._parses:
        if parse.root_node is None:
            continue
        lang_cls = LANGUAGE_BY_ID.get(parse.language)
        if lang_cls is None:
            continue
        queries = lang_cls.type_annotation_queries()
        if not queries:
            continue
        ts_lang = lang_cls.grammar()
        for query_str, kind in queries:
            for _, captures in _matches(ts_lang, query_str, parse.root_node):
                for node in _annotation_nodes(captures):
                    text = parse.content[node.start_byte:node.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                    out.append(TypeAnnotation(
                        file=str(parse.path),
                        text=text,
                        line=node.start_point[0] + 1,
                        kind=kind,
                        is_escape=lang_cls.is_escape_hatch_text(text),
                    ))
    return out


def _matches(ts_lang, query_str, root_node):
    """Run a tree-sitter query and yield (idx, captures) pairs.

    Supports both the modern Query/QueryCursor API and the legacy
    ``lang.query()`` API. Returns the raw matches; ``_annotation_nodes``
    extracts the ``@annotation`` captures.
    """
    import tree_sitter

    query_cls = getattr(tree_sitter, "Query", None)
    cursor_cls = getattr(tree_sitter, "QueryCursor", None)
    if query_cls is not None and cursor_cls is not None:
        query = query_cls(ts_lang, query_str)
        cursor = cursor_cls(query)
        for idx, captures in cursor.matches(root_node):
            yield idx, captures
        return

    query = ts_lang.query(query_str)
    for match in query.matches(root_node):
        if isinstance(match, tuple) and len(match) == 2:
            yield match


def _annotation_nodes(captures):
    """Yield every node captured under the ``@annotation`` name."""
    if isinstance(captures, dict):
        yield from captures.get("annotation", [])
        return
    for name, node in captures:
        if name == "annotation":
            yield node
