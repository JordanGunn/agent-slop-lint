"""Structure view — the substrate structural rules consume.

A ``Structure`` is a windowed view over the parsed corpus exposing
scopes, callables, and the parent/child relationships between them.

The view owns metric computations. Rules call methods like
``cyclomatic(c)``; AST walking happens inside the view, hidden behind
the compute API. See ``docs/planning/codebase.md`` for the locked
views-own-compute principle.

Slicing methods (``under``, ``where``) return NEW ``Structure``
instances over the same underlying parse data.
"""
from __future__ import annotations

from typing import Any, Callable as TypingCallable, Iterable, Sequence

from slop.tree.records import Callable, CallableKind, ParseResult, Scope, ScopeKind


# Per-language decision-node sets for cyclomatic complexity.
_CCX_DECISION_NODES: dict[str, frozenset[str]] = {
    "python": frozenset({
        "if_statement", "elif_clause", "for_statement", "while_statement",
        "except_clause", "conditional_expression", "case_clause",
    }),
}

_CCX_BOOL_OP_NODE: dict[str, str] = {
    "python": "boolean_operator",
}


class Structure:
    """View over the corpus exposing scopes + callables + compute methods."""

    def __init__(
        self,
        parses: Sequence[ParseResult],
        *,
        filters: Sequence[TypingCallable[[Any], bool]] = (),
    ) -> None:
        self._parses = tuple(parses)
        self._filters = tuple(filters)

        # Indexes built once at construction.
        self._language_by_path: dict[str, str] = {}
        self._callables_by_qualname: dict[str, Callable] = {}
        self._node_by_qualname: dict[str, Any] = {}
        self._content_by_qualname: dict[str, bytes] = {}

        for p in parses:
            self._language_by_path[str(p.path)] = p.language
            for c in p.callables:
                self._callables_by_qualname[c.qualname] = c
                if c.qualname in p.callable_nodes:
                    self._node_by_qualname[c.qualname] = p.callable_nodes[c.qualname]
                    self._content_by_qualname[c.qualname] = p.content

    # ---- iteration ---------------------------------------------------

    def scopes(self) -> Iterable[Scope]:
        for p in self._parses:
            for s in p.scopes:
                if all(f(s) for f in self._filters):
                    yield s

    def callables(self) -> Iterable[Callable]:
        for p in self._parses:
            for c in p.callables:
                if all(f(c) for f in self._filters):
                    yield c

    # ---- lookup ------------------------------------------------------

    def scope(self, qualname: str) -> Scope | None:
        for p in self._parses:
            for s in p.scopes:
                if s.qualname == qualname:
                    return s
        return None

    def children(self, scope: str) -> Iterable[Callable]:
        for c in self.callables():
            if c.parent == scope:
                yield c

    def language_for(self, record: Any) -> str | None:
        """Resolve a record's language via the internal path→language index.

        Records dropped their denormalised ``language`` field in the
        v2 refactor; views maintain the canonical mapping.
        """
        path = getattr(record, "path", None)
        if path is None:
            return None
        return self._language_by_path.get(str(path))

    # ---- compute methods (views own metric computations) -------------

    def cyclomatic(self, c: Callable) -> int:
        """McCabe cyclomatic complexity for one callable.

        Counts decision points + short-circuit boolean operators, plus
        1 for the base path (McCabe 1976: CCX = decisions + 1).
        """
        node = self._node_by_qualname.get(c.qualname)
        if node is None:
            return 1
        language = self._language_by_path.get(str(c.path))
        if language is None:
            return 1
        decision_nodes = _CCX_DECISION_NODES.get(language)
        bool_op_node = _CCX_BOOL_OP_NODE.get(language)
        if decision_nodes is None:
            return 1
        body = node.child_by_field_name("body")
        walk_from = body if body is not None else node
        count = _count_decisions(walk_from, decision_nodes, bool_op_node)
        return count + 1

    # ---- slicing -----------------------------------------------------

    def under(self, *, path: str | None = None) -> Structure:
        new_filters = list(self._filters)
        if path is not None:
            path_prefix = path
            new_filters.append(lambda rec: str(rec.path).startswith(path_prefix))
        return Structure(self._parses, filters=tuple(new_filters))

    def where(
        self,
        *,
        language: str | None = None,
        kind: ScopeKind | CallableKind | None = None,
    ) -> Structure:
        new_filters = list(self._filters)
        if language is not None:
            lang = language
            lang_map = self._language_by_path
            new_filters.append(lambda rec: lang_map.get(str(rec.path)) == lang)
        if kind is not None:
            k = kind
            new_filters.append(lambda rec: getattr(rec, "kind", None) == k)
        return Structure(self._parses, filters=tuple(new_filters))


def _count_decisions(
    node: Any,
    decision_nodes: frozenset[str],
    bool_op_node: str | None,
) -> int:
    """Recursively count cyclomatic decision points under ``node``."""
    nested_function_types = {"function_definition", "async_function_definition", "lambda"}
    count = 0
    stack = [node]
    while stack:
        cur = stack.pop()
        ctype = cur.type
        if ctype in nested_function_types and cur is not node:
            continue
        if ctype in decision_nodes:
            count += 1
        if bool_op_node is not None and ctype == bool_op_node:
            count += 1
        stack.extend(reversed(cur.children))
    return count
