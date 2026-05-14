"""Julia grammar — procedural; multimethods don't bind receivers.

Overrides ``extract_name`` because Julia's ``function_definition`` puts
the name inside ``signature → call_expression → identifier`` rather
than at ``child_by_field_name("name")``.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Callable as Node
from ..ast import Catch, Conditional, Identifier, Literal, Loop, Operator, Wrapper
from ..procedural import Procedural


class Julia(Procedural):
    id: ClassVar[str] = "julia"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Node.FUNCTION_DEFINITION, Node.ARROW_FUNCTION_EXPRESSION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT, Conditional.ELSEIF_CLAUSE,
            Loop.FOR_STATEMENT, Loop.WHILE_STATEMENT,
            Catch.CATCH_CLAUSE,
            Conditional.TERNARY_EXPRESSION,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.WHILE_STATEMENT,
            Catch.TRY_STATEMENT,                    # container for catch/finally clauses
            Catch.CATCH_CLAUSE,
            Conditional.TERNARY_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Conditional.ELSEIF_CLAUSE})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def if_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.IF_STATEMENT})

    @classmethod
    def elif_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.ELSEIF_CLAUSE})

    @classmethod
    def else_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.ELSE_CLAUSE})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({Loop.FOR_STATEMENT, Loop.WHILE_STATEMENT})

    @classmethod
    def try_nodes(cls) -> frozenset[str]:
        return frozenset({Catch.TRY_STATEMENT})

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        return frozenset({Catch.CATCH_CLAUSE})

    @classmethod
    def body_field(cls) -> str:
        # Flat-body language: function/branch statements are direct
        # children rather than wrapped in a block node. The walker
        # iterates children and filters by body_skip_types.
        return ""

    @classmethod
    def body_skip_types(cls) -> frozenset[str]:
        return frozenset({
            "function", "end", "signature",
            "if", "elseif", "else", "for", "for_binding",
            "while", "try", "catch", "finally", "do",
        })

    @classmethod
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        # Julia's ``::`` operator creates ``typed_expression`` binary nodes.
        # The right side of the binary is the annotation; capture every
        # node whose parent is a typed_expression and whose left sibling
        # is the bound identifier.
        return (
            ("(typed_expression . (_) (_) @annotation)", "annotation"),
        )

    @classmethod
    def is_escape_hatch_text(cls, text: str) -> bool:
        cleaned = text.strip().lstrip(":").strip()
        return cleaned == "Any" or cleaned.endswith(".Any")

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            # ``using Foo`` / ``using Foo, Bar``
            ("(using_statement (identifier) @module)", "julia_using"),
            # ``using Foo.Bar``
            ("(using_statement (scoped_identifier) @module)", "julia_using"),
            # ``using Foo: a, b`` — only the leading identifier is the module
            ("(using_statement (selected_import . (identifier) @module))", "julia_using"),
            # ``import Foo`` / ``import Foo, Bar``
            ("(import_statement (identifier) @module)", "julia_import"),
            # ``import Foo.Bar``
            ("(import_statement (scoped_identifier) @module)", "julia_import"),
            # ``import Base: show`` — only the leading identifier is the module
            ("(import_statement (selected_import . (identifier) @module))", "julia_import"),
        )

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.INTEGER_LITERAL, Literal.FLOAT_LITERAL})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            # Keywords
            "function", "return", "if", "else", "elseif", "end",
            "for", "while", "break", "continue", "in",
            "try", "catch", "finally", "throw",
            "do", "begin", "let", "global", "local",
            "module", "using", "import", "export",
            "struct", "mutable", "abstract", "primitive", "type",
            "const",
            # Operator-symbol tokens (tree-sitter-julia commonly wraps
            # these as named ``operator`` children; the literal-text
            # match still finds bare-token nodes that some operator
            # syntactic positions expose).
            "=", "+", "-", "*", "/", "%", "^", "//", ".",
            "==", "!=", "<", ">", "<=", ">=", "===", "!==",
            "&&", "||", "!", "&", "|", "<<", ">>",
            "+=", "-=", "*=", "/=",
            "->", "::", ":", "?", "@", "...",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "integer_literal", "float_literal",
            "string_literal", "character_literal",
            "true", "false", "nothing", "missing",
        })

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Walk Julia's ``signature → call_expression → identifier`` chain.

        Julia's tree-sitter exposes ``signature`` as a positional child
        (no field name), and ``call_expression`` as a positional child
        of ``signature``. Identifier is the first child of
        ``call_expression``.
        """
        if node.type == Node.ARROW_FUNCTION_EXPRESSION:
            return "<lambda>"
        if node.type != Node.FUNCTION_DEFINITION:
            return super().extract_name(node, content)
        # Find signature child (positional, no field name).
        signature = next(
            (c for c in node.children if c.type == Wrapper.SIGNATURE),
            None,
        )
        if signature is None:
            return "<anonymous>"
        # Find call_expression inside signature.
        call_expr = next(
            (c for c in signature.children if c.type == Wrapper.CALL_EXPRESSION),
            None,
        )
        if call_expr is None:
            return "<anonymous>"
        # First identifier child of call_expression is the function name.
        ident = next(
            (c for c in call_expr.children if c.type == Identifier.IDENTIFIER),
            None,
        )
        if ident is None:
            return "<anonymous>"
        return content[ident.start_byte:ident.end_byte].decode("utf-8", errors="replace")
