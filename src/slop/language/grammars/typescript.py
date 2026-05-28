"""TypeScript grammar — classes + interfaces + free functions.

Like JavaScript, syntactically distinguishes function/method node types.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Block, Callable, Catch, Conditional, Identifier, Literal, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class TypeScript(MultiPurpose):
    id: ClassVar[str] = "typescript"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Callable.FUNCTION_DECLARATION, Callable.FUNCTION_EXPRESSION,
            Callable.ARROW_FUNCTION, Callable.METHOD_DEFINITION,
            Callable.GENERATOR_FUNCTION_DECLARATION,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({
            Scope.CLASS_DECLARATION,
            Scope.INTERFACE_DECLARATION,
            Scope.ABSTRACT_CLASS_DECLARATION,
        })

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({
            Identifier.IDENTIFIER, Identifier.PROPERTY_IDENTIFIER, Identifier.TYPE_IDENTIFIER,
        })

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
            Switch.SWITCH_STATEMENT,
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
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(import_statement source: (string (string_fragment) @module))", "esm"),
            (
                "((call_expression function: (identifier) @fn"
                " arguments: (arguments (string (string_fragment) @module)))"
                " (#eq? @fn \"require\"))",
                "require",
            ),
        )

    @classmethod
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        # tree-sitter-typescript wraps both parameter annotations and
        # return-type annotations in ``type_annotation`` nodes whose
        # child is the bare type. ``predefined_type`` is the bare-keyword
        # form (``any``, ``string``, ``number``, ``unknown``, ``void``).
        return (
            ("(type_annotation (_) @annotation)", "annotation"),
        )

    @classmethod
    def is_escape_hatch_text(cls, text: str) -> bool:
        cleaned = text.strip().lstrip(":").strip()
        # Also count ``unknown`` when explicitly used as an escape
        # hatch — but TS conventionally treats unknown as safer than
        # any, so we restrict to literal ``any``.
        return cleaned == "any" or "any" in _ts_type_tokens(cleaned)

    @classmethod
    def hidden_mutators(
        cls, fn_node: Any, content: bytes,
        *,
        require_type_annotation: bool = True,
    ) -> list[tuple[str, str, int]]:
        # Delegate to JavaScript's logic — same call shape, plus TS's
        # type-annotation gating when require_type_annotation is True.
        from .javascript import _js_walk_mutations, _ts_parameter_names_with_annotation

        params = _ts_parameter_names_with_annotation(
            fn_node, content, require_type_annotation,
        )
        if not params:
            return []
        body = fn_node.child_by_field_name("body") or fn_node
        return _js_walk_mutations(body, content, params)

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        """Interfaces are abstract; ``abstract class`` is abstract; classes otherwise concrete."""
        ntype = node.type
        if ntype == Scope.INTERFACE_DECLARATION:
            return True
        if ntype == "abstract_class_declaration":
            return True
        if ntype == Scope.CLASS_DECLARATION:
            # ``abstract`` modifier appears as a direct child token.
            for child in node.children:
                if child.type == "abstract":
                    return True
                text = content[child.start_byte:child.end_byte].decode(
                    "utf-8", errors="replace",
                ).strip()
                if text == "abstract":
                    return True
            return False
        return None

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
            "interface", "type", "enum", "as",
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
            "type_identifier",
            "number", "string", "string_fragment",
            "template_string", "regex",
            "true", "false", "null", "undefined",
        })

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """TS: ``class_heritage`` with ``extends_clause`` and ``implements_clause``."""
        out: list[str] = []
        for child in node.children:
            if child.type == "class_heritage":
                for clause in child.children:
                    if clause.type in ("extends_clause", "implements_clause"):
                        for c in clause.children:
                            if c.type in ("type_identifier", "identifier"):
                                out.append(content[c.start_byte:c.end_byte].decode("utf-8", errors="replace"))
        return out


def _ts_type_tokens(text: str) -> set[str]:
    """Split a TypeScript type-annotation text into top-level token names.

    ``string | any`` → {string, any}; ``Array<any>`` → {Array, any};
    ``{x: any}`` → {x, any}.
    """
    out: set[str] = set()
    buf: list[str] = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            buf.append(ch)
        else:
            if buf:
                out.add("".join(buf))
                buf = []
    if buf:
        out.add("".join(buf))
    return out
