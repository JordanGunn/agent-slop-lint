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


def _js_parameter_names(fn_node: Any, content: bytes) -> set[str]:
    params_node = fn_node.child_by_field_name("parameters") or fn_node.child_by_field_name("parameter")
    if params_node is None:
        # Arrow functions with a single bare identifier parameter.
        for child in fn_node.children:
            if child.type == "identifier":
                return {content[child.start_byte:child.end_byte].decode(
                    "utf-8", errors="replace",
                )}
        return set()
    names: set[str] = set()
    for child in params_node.children:
        if child.type == "identifier":
            names.add(content[child.start_byte:child.end_byte].decode(
                "utf-8", errors="replace",
            ))
        elif child.type in ("assignment_pattern",):
            left = child.child_by_field_name("left")
            if left is not None and left.type == "identifier":
                names.add(content[left.start_byte:left.end_byte].decode(
                    "utf-8", errors="replace",
                ))
    return names


_TS_MUTABLE_TYPES: frozenset[str] = frozenset({
    "Array", "Map", "Set", "WeakMap", "WeakSet",
    "ReadonlyArray",  # commonly mutated despite the read-only annotation
})


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
        # tree-sitter-typescript wraps params in ``required_parameter`` /
        # ``optional_parameter`` nodes that contain the pattern (identifier)
        # and an optional ``type_annotation`` field.
        if child.type not in ("required_parameter", "optional_parameter"):
            continue
        pattern = child.child_by_field_name("pattern")
        if pattern is None or pattern.type != "identifier":
            continue
        name = content[pattern.start_byte:pattern.end_byte].decode(
            "utf-8", errors="replace",
        )
        type_ann = child.child_by_field_name("type")
        if not require_annotation:
            names.add(name)
            continue
        if type_ann is None:
            continue
        type_text = content[type_ann.start_byte:type_ann.end_byte].decode(
            "utf-8", errors="replace",
        )
        tokens: set[str] = set()
        buf: list[str] = []
        for ch in type_text:
            if ch.isalnum() or ch == "_":
                buf.append(ch)
            else:
                if buf:
                    tokens.add("".join(buf))
                    buf = []
        if buf:
            tokens.add("".join(buf))
        if tokens & _TS_MUTABLE_TYPES:
            names.add(name)
    return names


def _js_walk_mutations(
    body: Any, content: bytes, params: set[str],
) -> list[tuple[str, str, int]]:
    out: list[tuple[str, str, int]] = []
    stack = [body]
    while stack:
        n = stack.pop()
        if n.type == "call_expression":
            fn_child = n.child_by_field_name("function")
            if fn_child is not None and fn_child.type == "member_expression":
                obj = fn_child.child_by_field_name("object")
                prop = fn_child.child_by_field_name("property")
                if (
                    obj is not None and prop is not None
                    and obj.type == "identifier"
                    and prop.type in ("property_identifier", "identifier")
                ):
                    obj_name = content[obj.start_byte:obj.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                    method = content[prop.start_byte:prop.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                    if obj_name in params and method in _JS_MUTATION_METHODS:
                        out.append((obj_name, method, n.start_point[0] + 1))
        stack.extend(n.children)
    return out
