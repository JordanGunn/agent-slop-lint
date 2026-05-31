"""Module import extraction — raw ImportDecl per module.

Ported from the legacy structure/imports.py extraction half: run the grammar's
import_queries against the module's AST root, capture @module strings, filter to
module-level (drop TYPE_CHECKING-guarded and function-local imports — they are
not runtime edges). Resolution into a graph lives in model/dependency.py.
"""
from __future__ import annotations

from typing import Any

from ..component.metrics import ImportDecl

_STRIP = "\"'<>"
_NON_MODULE_LEVEL_PARENTS = frozenset({"function_definition", "decorated_definition"})


def module_imports(module: Any) -> list[ImportDecl]:
    grammar = module._grammar
    queries = grammar.import_queries()
    root = module._node
    if not queries or root is None:
        return []
    content = module._content
    ts_lang = grammar.ts_language()
    if ts_lang is None:
        return []
    out: list[ImportDecl] = []
    for query_str, kind in queries:
        for node in _module_captures(ts_lang, query_str, root):
            if not _is_module_level(node):
                continue
            text = content[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip(_STRIP)
            if text:
                out.append(ImportDecl(specifier=text, kind=kind, line=node.start_point[0] + 1))
    return out


def _is_module_level(node: Any) -> bool:
    cur = node.parent
    while cur is not None:
        if cur.type in _NON_MODULE_LEVEL_PARENTS:
            return False
        if cur.type == "if_statement":
            cond = cur.child_by_field_name("condition")
            if cond is not None and cond.type == "identifier" and cond.text == b"TYPE_CHECKING":
                return False
        cur = cur.parent
    return True


def _module_captures(ts_lang: Any, query_str: str, root: Any):
    import tree_sitter

    query_cls = getattr(tree_sitter, "Query", None)
    cursor_cls = getattr(tree_sitter, "QueryCursor", None)
    if query_cls is not None and cursor_cls is not None:
        cursor = cursor_cls(query_cls(ts_lang, query_str))
        for _idx, captures in cursor.matches(root):
            yield from _from_captures(captures)
        return
    query = ts_lang.query(query_str)
    for match in query.matches(root):
        if isinstance(match, tuple) and len(match) == 2:
            yield from _from_captures(match[1])


def _from_captures(captures):
    if isinstance(captures, dict):
        yield from captures.get("module", [])
        return
    for name, node in captures:
        if name == "module":
            yield node
