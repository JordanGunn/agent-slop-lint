"""Name binding: what each name in a file refers to.

A grammar states its scoping in a tree-sitter locals query (``ast/grammar/locals/<id>.scm``),
in the standard capture vocabulary: ``@local.scope`` opens a scope, ``@local.definition.<kind>``
defines a name in the innermost scope, ``@local.reference`` uses one. The kinds are
``parameter``, ``var``, ``import``, ``field`` and ``method`` (the Helix and nvim-treesitter
convention), plus
``@local.reference.member`` for a name that always denotes an instance field (Ruby ``@x``), and
``@local.definition-value`` for a definition's value, inside which the definition is not visible.
A class's field definitions are its properties: declared fields, struct fields, and the
members its methods assign through the instance (``self.x = ...``, ``this.x = ...``, ``@x = ...``).

Resolution follows ``tree-sitter-highlight``: a reference binds to the nearest enclosing scope
that defines its text, and within a scope to the latest definition before it. Two departures,
each from the languages' own rules:

- a ``field`` or ``method`` definition is visible throughout its scope, wherever it is declared
  (JLS §6.3: the scope of a member is the entire class body);
- where a grammar's bindings are hoisted (``hoisted_bindings``: Python, JavaScript, TypeScript,
  Julia), a name binds to its scope's definition even when the definition comes later;
- when a grammar's methods do not see their class body's names (``class_scope_visible`` is
  false: Python, JavaScript, TypeScript, Go, Rust), a class scope is skipped on the way out.

When one node is captured by several patterns, the first pattern in the query wins, as in
``tree-sitter-highlight``; so definition patterns come before the catch-all reference, and
``@ignore`` (a member name after a receiver, a keyword argument's name) comes before both.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import cache
from pathlib import Path
from typing import Any

_LOCALS = Path(__file__).parent / "grammar" / "locals"


class SymbolKind(Enum):
    """What a name occurrence binds to (the Roslyn and LSP term), or ``FREE`` for a free name."""

    PARAMETER = "parameter"   # a parameter of an enclosing callable
    LOCAL = "local"           # a variable an enclosing scope defines
    IMPORT = "import"         # a name an enclosing scope imports: its text names another module's entity
    FIELD = "field"           # a field of the enclosing class
    METHOD = "method"         # a method of the enclosing class
    FREE = "free"             # nothing in this file: a global, a builtin, an import's member


_VALUE = "local.definition-value"
_QUERIES: dict[str, Any] = {}     # grammar id -> compiled locals query
_HOISTED = frozenset({"field", "method"})
_KIND_OF = {"parameter": SymbolKind.PARAMETER, "var": SymbolKind.LOCAL, "import": SymbolKind.IMPORT, "field": SymbolKind.FIELD, "method": SymbolKind.METHOD}


@dataclass(frozen=True)
class Binding:
    """One name occurrence: its text and bytes, the kind of symbol it binds to, the byte where
    that definition starts (None when free), and whether this occurrence is itself the definition."""

    text: str
    start: int
    end: int
    kind: SymbolKind
    definition: int | None
    defines: bool


@dataclass
class _Scope:
    start: int
    end: int
    is_class: bool
    parent: _Scope | None
    # text -> (byte, kind, value start, value end): a definition is not visible in its own value
    names: dict[str, list[tuple[int, str, int, int]]] = field(default_factory=dict)


@cache
def locals_query(grammar_id: str) -> str | None:
    """The grammar's locals query text, or None if it has none."""
    path = _LOCALS / f"{grammar_id}.scm"
    return path.read_text(encoding="utf-8") if path.exists() else None


def bind(root: Any, content: bytes, grammar: Any) -> dict[int, Binding]:
    """Every captured name occurrence under the raw tree-sitter node ``root``, keyed by start byte.
    Empty when the grammar has no locals query."""
    captures = _captures(root, grammar)
    if captures is None:
        return {}
    visible, hoisted = bool(grammar.class_scope_visible()), bool(grammar.hoisted_bindings())
    return {node.start_byte: _resolve(node, capture, scope, content, visible, hoisted)
            for node, capture, scope in _collect(root, content, captures, grammar.classes())}


def _collect(root: Any, content: bytes, captures: list, classes: frozenset[str]) -> list[tuple[Any, str, _Scope]]:
    """Open the scopes and record each definition in its scope, in source order; return every
    name occurrence with the scope it was seen in, ready to resolve."""
    top = _Scope(root.start_byte, root.end_byte, False, None)
    stack = [top]
    pending: list[tuple[Any, str, _Scope]] = []
    for node, capture, value in captures:
        while stack[-1] is not top and node.start_byte >= stack[-1].end:
            stack.pop()
        if capture == "local.scope":
            is_class = node.type in classes or (node.parent is not None and node.parent.type in classes)
            stack.append(_Scope(node.start_byte, node.end_byte, is_class, stack[-1]))
            continue
        text = content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
        scope = _owner(stack[-1], node)
        if capture.startswith("local.definition"):
            kind = capture.rsplit(".", 1)[-1] if capture.count(".") == 2 else "var"
            scope.names.setdefault(text, []).append((node.start_byte, kind, *value))
        pending.append((node, capture, scope))
    return pending


def _owner(scope: _Scope, node: Any) -> _Scope:
    """The scope a name belongs to: a declaration's own name (``def f``, ``class A``,
    ``int f(int x)``) belongs to the scope containing the declaration, not to the scope the
    declaration opens."""
    declaration = _declaration_named(node)
    if scope.parent is not None and declaration is not None and (declaration.start_byte, declaration.end_byte) == (scope.start, scope.end):
        return scope.parent
    return scope


def _declaration_named(node: Any) -> Any | None:
    """The declaration whose name ``node`` is: its parent's ``name`` field, or the innermost end
    of a C-style ``declarator`` chain (``f`` in ``int *f(int x)``)."""
    child, parent = node, node.parent
    while parent is not None and parent.child_by_field_name("declarator") == child:
        child, parent = parent, parent.parent
    if child is not node:
        return child
    return parent if parent is not None and parent.child_by_field_name("name") == node else None


def _resolve(node: Any, capture: str, scope: _Scope, content: bytes, class_scope_visible: bool,
             hoisted: bool) -> Binding:
    text = content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
    start = node.start_byte
    if capture == "local.reference.member":
        return Binding(text, start, node.end_byte, SymbolKind.FIELD, None, False)
    defines = capture.startswith("local.definition")
    current: _Scope | None = scope
    left_function = False
    while current is not None:
        if current.is_class and left_function and not class_scope_visible:
            current = current.parent
            continue
        found = _visible(current.names.get(text, ()), start, hoisted)
        if found is not None:
            byte, kind = found[:2]
            return Binding(text, start, node.end_byte, _KIND_OF.get(kind, SymbolKind.LOCAL), byte, defines)
        left_function = left_function or not current.is_class
        current = current.parent
    return Binding(text, start, node.end_byte, SymbolKind.FREE, None, defines)


def _visible(definitions: Any, at: int, hoisted: bool) -> tuple[int, str, int, int] | None:
    """The definition a name at byte ``at`` sees in one scope. A member, or any name where
    bindings are hoisted, is one symbol for the whole scope: its first definition. Elsewhere a
    later definition is a new symbol (Rust's ``let x = x + 1``), so a name sees the latest
    definition at or before it (a definition sees itself). No definition is visible inside its
    own value (``@local.definition-value``): ``x`` in ``let x = x + 1`` is the earlier ``x``."""
    definitions = [d for d in definitions if not d[2] <= at < d[3]]
    members = [d for d in definitions if d[1] in _HOISTED]
    if members or hoisted:
        return min(members or definitions, default=None)
    before = [d for d in definitions if d[0] <= at]
    return max(before) if before else None


def _captures(root: Any, grammar: Any) -> list[tuple[Any, str, tuple[int, int]]] | None:
    """``(node, capture name, value span)`` in source order, outer scopes before what they
    contain, one capture per node: the one from the earliest pattern. The value span is the
    definition's ``@local.definition-value`` in the same match, else empty."""
    query = _query(grammar)
    if query is None:
        return None
    import tree_sitter

    chosen: dict[tuple[int, int, str], tuple[int, Any, str, tuple[int, int]]] = {}
    for pattern, node, name, value in _tagged(tree_sitter.QueryCursor(query).matches(root)):
        key = (node.start_byte, node.end_byte, "scope:" + node.type if name == "local.scope" else node.type)
        if key not in chosen or pattern < chosen[key][0]:
            chosen[key] = (pattern, node, name, value)
    ordered = sorted(chosen.values(), key=lambda c: (c[1].start_byte, -c[1].end_byte, c[2] != "local.scope"))
    return [(node, name, value) for _, node, name, value in ordered if name != "ignore"]


def _tagged(matches: Any):
    """``(pattern, node, capture name, value span)`` for every capture the resolver reads."""
    for pattern, captures in matches:
        values = captures.get(_VALUE, ())
        value = (values[0].start_byte, values[-1].end_byte) if values else (0, 0)
        for name, nodes in captures.items():
            if name != _VALUE and (name.startswith("local.") or name == "ignore"):
                for node in nodes:
                    yield pattern, node, name, value


def _query(grammar: Any) -> Any | None:
    """The grammar's compiled locals query, compiled once; None if it has none."""
    if grammar.id not in _QUERIES:
        text, language = locals_query(grammar.id), grammar.ts_language()
        if text is None or language is None:
            return None
        import tree_sitter

        _QUERIES[grammar.id] = tree_sitter.Query(language, text)
    return _QUERIES[grammar.id]
