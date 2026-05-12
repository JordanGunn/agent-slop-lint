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

from slop.language.grammars import LANGUAGE_BY_ID
from slop.tree.records import Callable, CallableKind, ParseResult, Scope, ScopeKind


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

        # Per-callable indexes keyed by (path, qualname) — a bare qualname
        # like ``a.f`` collides across same-file-stem corpora (a.py + a.js
        # both yield ``a.f``); pairing it with the absolute path scopes
        # the lookup to its source file.
        self._language_by_path: dict[str, str] = {}
        self._callables_by_key: dict[tuple[str, str], Callable] = {}
        self._node_by_key: dict[tuple[str, str], Any] = {}
        self._content_by_key: dict[tuple[str, str], bytes] = {}

        for p in parses:
            self._language_by_path[str(p.path)] = p.language
            for c in p.callables:
                key = (str(c.path), c.qualname)
                self._callables_by_key[key] = c
                if c.qualname in p.callable_nodes:
                    self._node_by_key[key] = p.callable_nodes[c.qualname]
                    self._content_by_key[key] = p.content

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

        Per-language node types come from the ``Language`` class via
        ``decision_nodes()``, ``boolean_op_node()``, and
        ``boolean_op_operators()``. ``definition_unwrap_types`` is
        honoured so C++ ``template_declaration`` wrappers descend to
        the actual function body. Languages whose grammar doesn't
        declare ``decision_nodes`` return CCX=1 (the base path).
        """
        key = (str(c.path), c.qualname)
        node = self._node_by_key.get(key)
        if node is None:
            return 1
        content = self._content_by_key.get(key)
        if content is None:
            return 1
        language_id = self._language_by_path.get(str(c.path))
        if language_id is None:
            return 1
        lang = LANGUAGE_BY_ID.get(language_id)
        if lang is None:
            return 1
        decision_nodes = lang.decision_nodes()
        if not decision_nodes:
            return 1
        walk_from = _resolve_body(node, lang.definition_unwrap_types())
        count = _count_decisions(
            walk_from,
            decision_nodes,
            lang.boolean_op_node(),
            lang.boolean_op_operators(),
            lang.callable(),
            content,
        )
        return count + 1

    def cognitive(self, c: Callable) -> int:
        """Cognitive Complexity for one callable (Campbell 2018).

        Differs from cyclomatic in three ways:

          1. **Nesting penalty.** Each decision point inside a nesting
             container adds ``1 + depth`` (instead of just 1). Deeply
             nested branches cost more than flat ones.
          2. **Compensating decisions.** Syntactic children of a
             nesting container that are logically peers (``elif_clause``
             of ``if_statement``, ``switch_case`` of ``switch_statement``)
             add ``1 + max(0, depth - 1)`` — they don't double-charge
             for the parent's nesting bump.
          3. **Sequence collapsing on boolean operators.** A short-
             circuit operator counts +1 only when it isn't continuing a
             same-operator chain (``a && b && c`` contributes 1, not 2;
             ``a && b || c`` contributes 2).

        Per-language node sets come from the ``Language`` class via
        ``decision_nodes()``, ``nesting_nodes()``,
        ``compensating_decisions()``, ``boolean_op_node()``, and
        ``boolean_op_operators()``.
        """
        key = (str(c.path), c.qualname)
        node = self._node_by_key.get(key)
        if node is None:
            return 0
        content = self._content_by_key.get(key)
        if content is None:
            return 0
        language_id = self._language_by_path.get(str(c.path))
        if language_id is None:
            return 0
        lang = LANGUAGE_BY_ID.get(language_id)
        if lang is None:
            return 0
        decision_nodes = lang.decision_nodes()
        if not decision_nodes:
            return 0
        walk_from = _resolve_body(node, lang.definition_unwrap_types())
        return _cognitive_walk(
            walk_from,
            decision_nodes,
            lang.nesting_nodes(),
            lang.compensating_decisions(),
            lang.boolean_op_node(),
            lang.boolean_op_operators(),
            lang.callable(),
            content,
        )

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


def _resolve_body(node: Any, unwrap: frozenset[str]) -> Any:
    """Descend through wrapper nodes (e.g. C++ ``template_declaration``)
    to the actual definition's body field. Falls back to the node itself
    when no body field exists.
    """
    current = node
    # Unwrap up to a small fixed depth — guards against malformed ASTs.
    for _ in range(4):
        if current.type not in unwrap:
            break
        # Find the wrapped definition among the children.
        next_node = None
        for child in current.children:
            if child.type != current.type and child.type not in ("(", ")", "<", ">", ","):
                next_node = child
                break
        if next_node is None:
            break
        current = next_node
    body = current.child_by_field_name("body")
    return body if body is not None else current


def _count_decisions(
    node: Any,
    decision_nodes: frozenset[str],
    bool_op_node: str | None,
    bool_op_operators: frozenset[str] | None,
    nested_callables: frozenset[str],
    content: bytes,
) -> int:
    """Recursively count cyclomatic decision points under ``node``.

    ``nested_callables`` is the per-language set of node types that
    define a new callable scope (i.e. ``Language.callable()``). The
    walk does not descend into nested callables — each callable's
    metric is body-local. Honours per-language short-circuit operator
    filtering: when ``bool_op_operators`` is None, every
    ``bool_op_node`` instance counts (Python's dedicated
    ``boolean_operator``); when non-None, only nodes whose operator
    text is in the set count (C-family ``binary_expression`` with
    ``&&``/``||``/``??``).
    """
    count = 0
    stack = [node]
    while stack:
        cur = stack.pop()
        ctype = cur.type
        if ctype in nested_callables and cur is not node:
            continue
        if ctype in decision_nodes:
            count += 1
        if bool_op_node is not None and ctype == bool_op_node:
            if bool_op_operators is None or _bool_op_matches(cur, bool_op_operators, content):
                count += 1
        stack.extend(reversed(cur.children))
    return count


def _bool_op_matches(
    node: Any,
    operators: frozenset[str],
    content: bytes,
) -> bool:
    """True if ``node``'s operator text is in ``operators``.

    Tree-sitter grammars expose the operator in three different shapes:
      1. As an ``operator`` field on the binary node (JS/TS/Go/Java/C#).
      2. As a named child node of type ``operator`` (Julia, Ruby).
      3. As an unnamed punctuation token between the operands (some
         older grammars).
    All three are handled.
    """
    op_text = _bool_op_text(node, content)
    return op_text in operators if op_text else False


def _bool_op_text(node: Any, content: bytes) -> str:
    """Extract the operator text from a boolean/binary operator node.

    Tree-sitter grammars expose the operator in four shapes:
      1. As an ``operator`` field on the binary node (JS/TS/Go/Java/C#/C/C++).
      2. As a named child node of type ``operator`` (Julia, Ruby).
      3. As a child whose type name IS the operator keyword (Python:
         ``and`` / ``or`` / ``not``).
      4. As an unnamed punctuation token between operands.

    Returns the operator text or ``""`` if no operator child can be found.
    """
    op_node = node.child_by_field_name("operator")
    if op_node is not None:
        return content[op_node.start_byte:op_node.end_byte].decode("utf-8", errors="replace")
    for child in node.children:
        if child.type == "operator":
            return content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
        if child.type in ("and", "or", "not"):
            return child.type
        if not child.is_named:
            text = content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            if text in ("&&", "||", "??", "and", "or"):
                return text
    return ""


def _cognitive_walk(
    root: Any,
    decision_nodes: frozenset[str],
    nesting_nodes: frozenset[str],
    compensating: frozenset[str],
    bool_op_node: str | None,
    bool_op_operators: frozenset[str] | None,
    nested_callables: frozenset[str],
    content: bytes,
) -> int:
    """Walk ``root`` accumulating Cognitive Complexity (Campbell 2018).

    Iterative stack walk where each entry carries the current nesting
    depth. Each decision node contributes ``1 + depth``; compensating
    decisions contribute ``1 + max(0, depth - 1)``. Short-circuit
    operators count +1 unless they're continuing a same-operator chain
    with their syntactic parent (tree-sitter ``node.parent``).
    """
    cog = 0
    stack: list[tuple[Any, int]] = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        ctype = node.type

        # Skip nested callables; each gets its own metric.
        if ctype in nested_callables and node is not root:
            continue

        # Decision contribution.
        if ctype in decision_nodes:
            if ctype in compensating:
                cog += 1 + max(0, depth - 1)
            else:
                cog += 1 + depth

        # Boolean operator with sequence collapsing.
        if bool_op_node is not None and ctype == bool_op_node:
            op_text = _bool_op_text(node, content)
            counts = (bool_op_operators is None) or (op_text in bool_op_operators)
            if counts:
                parent = node.parent
                in_continuing_sequence = False
                if parent is not None and parent.type == bool_op_node:
                    parent_op = _bool_op_text(parent, content)
                    parent_counts = (
                        bool_op_operators is None or parent_op in bool_op_operators
                    )
                    if parent_counts and parent_op == op_text:
                        in_continuing_sequence = True
                if not in_continuing_sequence:
                    cog += 1

        # Children inherit incremented depth if this node is a nester.
        new_depth = depth + 1 if ctype in nesting_nodes else depth
        for child in reversed(node.children):
            stack.append((child, new_depth))

    return cog
