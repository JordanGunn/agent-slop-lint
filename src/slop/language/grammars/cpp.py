"""C++ grammar — classes + free functions + namespaces.

Overrides ``extract_name`` to handle the declarator chain
(``function_declarator → identifier``), qualified identifiers
(out-of-line methods), operator overloads, and destructors.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Callable as Node
from ..ast import Catch, Conditional, Identifier, Loop, Operator, Scope, Switch, Wrapper
from ..multipurpose import MultiPurpose


class Cpp(MultiPurpose):
    id: ClassVar[str] = "cpp"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Node.FUNCTION_DEFINITION, Node.LAMBDA_EXPRESSION})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Scope.CLASS_SPECIFIER, Scope.STRUCT_SPECIFIER})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({
            Identifier.IDENTIFIER, Identifier.FIELD_IDENTIFIER, Identifier.TYPE_IDENTIFIER,
        })

    @classmethod
    def methods(cls) -> frozenset[str]:
        # Lambdas aren't methods.
        return frozenset({Node.FUNCTION_DEFINITION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOR_RANGE_LOOP,  # range-based for
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.CASE_STATEMENT,                    # case X: / default:
            Conditional.CONDITIONAL_EXPRESSION,       # ternary
            Catch.CATCH_CLAUSE,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOR_RANGE_LOOP,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_STATEMENT,
            Conditional.CONDITIONAL_EXPRESSION,
            Catch.TRY_STATEMENT,                      # container for catch_clause
            Catch.CATCH_CLAUSE,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Switch.CASE_STATEMENT})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def definition_unwrap_types(cls) -> frozenset[str]:
        return frozenset({Wrapper.TEMPLATE_DECLARATION})

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
            if declarator.type == Wrapper.FUNCTION_DECLARATOR:
                inner = declarator.child_by_field_name("declarator")
                if inner is None:
                    return "<anonymous>"
                if inner.type in (Identifier.IDENTIFIER, Identifier.FIELD_IDENTIFIER):
                    return content[inner.start_byte:inner.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                if inner.type == Identifier.QUALIFIED_IDENTIFIER:
                    for c in reversed(inner.children):
                        if c.type == Identifier.IDENTIFIER:
                            return content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            )
                    return "<anonymous>"
                if inner.type == Identifier.OPERATOR_NAME:
                    for c in inner.children:
                        if c.type != Identifier.OPERATOR:
                            return content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            ).strip()
                    return "<anonymous>"
                if inner.type == Identifier.DESTRUCTOR_NAME:
                    for c in inner.children:
                        if c.type == Identifier.IDENTIFIER:
                            return "~" + content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            )
                    return "<anonymous>"
                return "<anonymous>"
            if declarator.type in (
                Wrapper.POINTER_DECLARATOR, Wrapper.REFERENCE_DECLARATOR,
                Wrapper.PARENTHESIZED_DECLARATOR,
            ):
                declarator = declarator.child_by_field_name("declarator")
                continue
            break
        return "<anonymous>"
