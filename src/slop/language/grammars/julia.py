"""Julia grammar — procedural; multimethods don't bind receivers.

Overrides ``extract_name`` because Julia's ``function_definition`` puts
the name inside ``signature → call_expression → identifier`` rather
than at ``child_by_field_name("name")``.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..procedural import Procedural


class Julia(Procedural):
    id: ClassVar[str] = "julia"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_definition", "arrow_function_expression"})

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Walk Julia's ``signature → call_expression → identifier`` chain.

        Julia's tree-sitter exposes ``signature`` as a positional child
        (no field name), and ``call_expression`` as a positional child
        of ``signature``. Identifier is the first child of
        ``call_expression``. Short-form ``f(x) = ...`` is an
        ``assignment`` whose first child is a ``call_expression``
        directly.
        """
        if node.type == "arrow_function_expression":
            return "<lambda>"
        if node.type != "function_definition":
            return super().extract_name(node, content)
        # Find signature child (positional, no field name).
        signature = next(
            (c for c in node.children if c.type == "signature"),
            None,
        )
        if signature is None:
            return "<anonymous>"
        # Find call_expression inside signature.
        call_expr = next(
            (c for c in signature.children if c.type == "call_expression"),
            None,
        )
        if call_expr is None:
            return "<anonymous>"
        # First identifier child of call_expression is the function name.
        ident = next(
            (c for c in call_expr.children if c.type == "identifier"),
            None,
        )
        if ident is None:
            return "<anonymous>"
        return content[ident.start_byte:ident.end_byte].decode("utf-8", errors="replace")

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_statement", "elseif_clause",
            "for_statement", "while_statement",
            "catch_clause",
            "ternary_expression",
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_statement",
            "for_statement", "while_statement",
            "try_statement",            # container for catch/finally clauses
            "catch_clause",
            "ternary_expression",
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"elseif_clause"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})
