"""Module import extraction — raw ImportDecl per module.

Run the grammar's import_queries against the module's AST root via
``Node.query(..., capture="module")``, then filter to module-level (drop
TYPE_CHECKING-guarded and function-local imports — they are not runtime edges).
Resolution into a graph lives in model/dependency.py. tree-sitter is no longer
touched here: the query goes through the AST proxy.
"""
from __future__ import annotations

from typing import Any

from ..scope.metrics import ImportDecl

_STRIP = "\"'<>"
_NON_MODULE_LEVEL_PARENTS = frozenset({"function_definition", "decorated_definition"})


def module_imports(module: Any) -> list[ImportDecl]:
    grammar = module._grammar
    queries = grammar.import_queries()
    if not queries or module._node is None:
        return []
    root = module._ast_node()
    out: list[ImportDecl] = []
    for query_str, kind in queries:
        for node in root.query(query_str, capture="module"):
            if not _is_module_level(node):
                continue
            text = node.text.strip(_STRIP)
            if text:
                out.append(ImportDecl(specifier=text, kind=kind, line=node.line))
    return out


def _is_module_level(node: Any) -> bool:
    cur = node.parent
    while cur is not None:
        if cur.type in _NON_MODULE_LEVEL_PARENTS:
            return False
        if cur.type == "if_statement":
            cond = cur.field("condition")
            if cond is not None and cond.type == "identifier" and cond.text == "TYPE_CHECKING":
                return False
        cur = cur.parent
    return True
