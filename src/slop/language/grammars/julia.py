"""Julia grammar — procedural; multimethods don't bind receivers.

Overrides ``extract_name`` because Julia's ``function_definition`` puts
the name inside ``signature → call_expression → identifier`` rather
than at ``child_by_field_name("name")``.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Callable as Node
from ..ast import Catch, Conditional, Identifier, Loop, Operator, Wrapper
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
