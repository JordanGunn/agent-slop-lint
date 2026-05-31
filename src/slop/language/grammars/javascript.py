"""JavaScript grammar — classes + free functions + arrow functions.

Tree-sitter-javascript syntactically distinguishes ``function_declaration``
and ``arrow_function`` (free) from ``method_definition`` (class-bound).
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Block, Callable, Catch, Conditional, Identifier, Literal, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class JavaScript(MultiPurpose):
    id: ClassVar[str] = "javascript"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Callable.FUNCTION_DECLARATION, Callable.FUNCTION_EXPRESSION,
            Callable.ARROW_FUNCTION, Callable.METHOD_DEFINITION,
            Callable.GENERATOR_FUNCTION_DECLARATION,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Scope.CLASS_DECLARATION})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({Identifier.IDENTIFIER, Identifier.PROPERTY_IDENTIFIER})

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({
            Callable.FUNCTION_DECLARATION, Callable.FUNCTION_EXPRESSION,
            Callable.ARROW_FUNCTION, Callable.GENERATOR_FUNCTION_DECLARATION,
        })

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({Callable.METHOD_DEFINITION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOR_IN_STATEMENT, Loop.FOR_OF_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_CASE,
            Catch.CATCH_CLAUSE,
            Conditional.TERNARY_EXPRESSION,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOR_IN_STATEMENT, Loop.FOR_OF_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_STATEMENT,                # container for switch_case
            Catch.CATCH_CLAUSE,
            Conditional.TERNARY_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_CASE})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||", "??"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({
            Loop.FOR_STATEMENT, Loop.FOR_IN_STATEMENT, Loop.FOR_OF_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
        })

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_STATEMENT})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_CASE})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({Block.STATEMENT_BLOCK})

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        return frozenset({Block.SWITCH_BODY})

    @classmethod
    def hidden_mutators(
        cls, fn_node: Any, content: bytes,
        *,
        require_type_annotation: bool = True,
    ) -> list[tuple[str, str, int]]:
        # JavaScript has no static type system to filter parameters by;
        # honour require_type_annotation as a literal skip when True.
        if require_type_annotation:
            return []
        # Extract parameter identifiers from formal_parameters.
        params = _js_parameter_names(fn_node, content)
        if not params:
            return []
        body = fn_node.child_by_field_name("body") or fn_node
        return _js_walk_mutations(body, content, params)

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        """JavaScript has no abstract-class concept — every class is concrete."""
        del content
        if node.type == Scope.CLASS_DECLARATION:
            return False
        return None

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(import_statement source: (string (string_fragment) @module))", "esm"),
            # CommonJS: ``const x = require('foo')`` — capture method=require
            # via predicate so it doesn't conflate with arbitrary calls.
            (
                "((call_expression function: (identifier) @fn"
                " arguments: (arguments (string (string_fragment) @module)))"
                " (#eq? @fn \"require\"))",
                "require",
            ),
        )

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.NUMBER})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "function", "if", "else", "for", "while", "do", "return",
            "class", "import", "from", "try", "catch", "finally",
            "throw", "new", "delete", "typeof", "instanceof", "void",
            "switch", "case", "default", "break", "continue",
            "var", "let", "const", "yield", "await", "async",
            "=", "+", "-", "*", "/", "%", "**",
            "==", "!=", "===", "!==", "<", ">", "<=", ">=",
            "&&", "||", "??", "!", "~", "&", "|", "^", "<<", ">>", ">>>",
            "+=", "-=", "*=", "/=", "%=", "**=",
            "++", "--", "=>", "...", "?",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "property_identifier", "shorthand_property_identifier",
            "number", "string", "string_fragment",
            "template_string", "regex",
            "true", "false", "null", "undefined",
        })

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """JS: ``class Foo extends Bar`` — class_heritage with bare identifier."""
        out: list[str] = []
        for child in node.children:
            if child.type == "class_heritage":
                for c in child.children:
                    if c.type == "identifier":
                        out.append(content[c.start_byte:c.end_byte].decode("utf-8", errors="replace"))
        return out


_JS_MUTATION_METHODS: frozenset[str] = frozenset({
    # Array
    "push", "pop", "splice", "shift", "unshift", "sort", "reverse", "fill",
    # Map / Set
    "set", "delete", "clear", "add",
})


def _identifier_child(node: Any) -> Any | None:
    """Return the first direct ``identifier`` child of a node, or None."""
    for c in node.children:
        if c.type == "identifier":
            return c
    return None


def _decode(node: Any, content: bytes) -> str:
    return content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _js_formal_param_name(child: Any, content: bytes) -> str | None:
    """Name of a JS formal parameter (bare identifier or ``x = default``)."""
    if child.type == "identifier":
        return _decode(child, content)
    if child.type == "assignment_pattern":
        left = child.child_by_field_name("left")
        if left is not None and left.type == "identifier":
            return _decode(left, content)
    return None


def _js_parameter_names(fn_node: Any, content: bytes) -> set[str]:
    params_node = fn_node.child_by_field_name("parameters") or fn_node.child_by_field_name("parameter")
    if params_node is None:
        # Arrow functions with a single bare identifier parameter.
        ident = _identifier_child(fn_node)
        return {_decode(ident, content)} if ident is not None else set()
    names: set[str] = set()
    for child in params_node.children:
        name = _js_formal_param_name(child, content)
        if name is not None:
            names.add(name)
    return names


_TS_MUTABLE_TYPES: frozenset[str] = frozenset({
    "Array", "Map", "Set", "WeakMap", "WeakSet",
    "ReadonlyArray",  # commonly mutated despite the read-only annotation
})


def _type_tokens(text: str) -> set[str]:
    """Split a type annotation into identifier-like tokens (``Array<number>``
    → {``Array``, ``number``})."""
    tokens: set[str] = set()
    buf: list[str] = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            buf.append(ch)
        elif buf:
            tokens.add("".join(buf))
            buf = []
    if buf:
        tokens.add("".join(buf))
    return tokens


def _ts_collection_param(child: Any, content: bytes, require_annotation: bool) -> str | None:
    """Name of a TS parameter, gated on a collection-type annotation when
    ``require_annotation`` is set. tree-sitter-typescript wraps params in
    ``required_parameter`` / ``optional_parameter`` nodes."""
    if child.type not in ("required_parameter", "optional_parameter"):
        return None
    pattern = child.child_by_field_name("pattern")
    if pattern is None or pattern.type != "identifier":
        return None
    name = _decode(pattern, content)
    if not require_annotation:
        return name
    type_ann = child.child_by_field_name("type")
    if type_ann is None:
        return None
    if _type_tokens(_decode(type_ann, content)) & _TS_MUTABLE_TYPES:
        return name
    return None


def _ts_parameter_names_with_annotation(
    fn_node: Any, content: bytes, require_annotation: bool,
) -> set[str]:
    """Extract parameter names; when annotation required, filter to
    collection-typed ones (Array / Map / Set / their generic forms)."""
    params_node = fn_node.child_by_field_name("parameters")
    if params_node is None:
        return set()
    names: set[str] = set()
    for child in params_node.children:
        name = _ts_collection_param(child, content, require_annotation)
        if name is not None:
            names.add(name)
    return names


def _js_mutation_call(n: Any, content: bytes, params: set[str]) -> tuple[str, str] | None:
    """``obj.method(...)`` where obj is a tracked param and method mutates."""
    fn_child = n.child_by_field_name("function")
    if fn_child is None or fn_child.type != "member_expression":
        return None
    obj = fn_child.child_by_field_name("object")
    prop = fn_child.child_by_field_name("property")
    if obj is None or prop is None:
        return None
    if obj.type != "identifier" or prop.type not in ("property_identifier", "identifier"):
        return None
    obj_name = _decode(obj, content)
    method = _decode(prop, content)
    if obj_name in params and method in _JS_MUTATION_METHODS:
        return (obj_name, method)
    return None


def _js_walk_mutations(
    body: Any, content: bytes, params: set[str],
) -> list[tuple[str, str, int]]:
    out: list[tuple[str, str, int]] = []
    stack = [body]
    while stack:
        n = stack.pop()
        if n.type == "call_expression":
            hit = _js_mutation_call(n, content, params)
            if hit is not None:
                out.append((hit[0], hit[1], n.start_point[0] + 1))
        stack.extend(n.children)
    return out
