"""C++ grammar — classes + free functions + namespaces.

Overrides ``extract_name`` to handle the declarator chain
(``function_declarator → identifier``), qualified identifiers
(out-of-line methods), operator overloads, and destructors.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Node
from ..multipurpose import MultiPurpose


class Cpp(MultiPurpose):
    id: ClassVar[str] = "cpp"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Node.FUNCTION_DEFINITION, Node.LAMBDA_EXPRESSION})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Node.CLASS_SPECIFIER, Node.STRUCT_SPECIFIER})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({Node.IDENTIFIER, Node.FIELD_IDENTIFIER, Node.TYPE_IDENTIFIER})

    @classmethod
    def methods(cls) -> frozenset[str]:
        # Lambdas aren't methods.
        return frozenset({Node.FUNCTION_DEFINITION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT, Node.FOR_RANGE_LOOP,  # range-based for
            Node.WHILE_STATEMENT, Node.DO_STATEMENT,
            Node.CASE_STATEMENT,            # case X: / default:
            Node.CONDITIONAL_EXPRESSION,    # ternary
            Node.CATCH_CLAUSE,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF_STATEMENT,
            Node.FOR_STATEMENT, Node.FOR_RANGE_LOOP,
            Node.WHILE_STATEMENT, Node.DO_STATEMENT,
            Node.SWITCH_STATEMENT,
            Node.CONDITIONAL_EXPRESSION,
            Node.TRY_STATEMENT,             # container for catch_clause
            Node.CATCH_CLAUSE,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Node.CASE_STATEMENT})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Node.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def definition_unwrap_types(cls) -> frozenset[str]:
        return frozenset({Node.TEMPLATE_DECLARATION})

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Walk the C++ declarator chain to find the function name.

        Handles plain functions, pointer/reference returns, in-class
        methods, out-of-line methods (qualified_identifier), operator
        overloads, destructors.
        """
        if node.type == Node.LAMBDA_EXPRESSION:
            return "<lambda>"
        if node.type != Node.FUNCTION_DEFINITION:
            # Fall back to default for non-function nodes (class_specifier etc.).
            return super().extract_name(node, content)
        declarator = node.child_by_field_name("declarator")
        for _ in range(8):
            if declarator is None:
                return "<anonymous>"
            if declarator.type == Node.FUNCTION_DECLARATOR:
                inner = declarator.child_by_field_name("declarator")
                if inner is None:
                    return "<anonymous>"
                if inner.type in (Node.IDENTIFIER, Node.FIELD_IDENTIFIER):
                    return content[inner.start_byte:inner.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                if inner.type == Node.QUALIFIED_IDENTIFIER:
                    for c in reversed(inner.children):
                        if c.type == Node.IDENTIFIER:
                            return content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            )
                    return "<anonymous>"
                if inner.type == Node.OPERATOR_NAME:
                    for c in inner.children:
                        if c.type != Node.OPERATOR:
                            return content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            ).strip()
                    return "<anonymous>"
                if inner.type == Node.DESTRUCTOR_NAME:
                    for c in inner.children:
                        if c.type == Node.IDENTIFIER:
                            return "~" + content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            )
                    return "<anonymous>"
                return "<anonymous>"
            if declarator.type in (
                Node.POINTER_DECLARATOR, Node.REFERENCE_DECLARATOR,
                Node.PARENTHESIZED_DECLARATOR,
            ):
                declarator = declarator.child_by_field_name("declarator")
                continue
            break
        return "<anonymous>"
