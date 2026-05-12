"""Ruby grammar — classes + modules + methods.

Tree-sitter-ruby uses ``method`` and ``singleton_method`` node types,
positional naming (no ``name`` field). Overrides ``extract_name`` to
skip ``def``/``self``/``.`` tokens.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Callable as Node
from ..ast import Catch, Conditional, Identifier, Literal, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class Ruby(MultiPurpose):
    id: ClassVar[str] = "ruby"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Node.METHOD, Node.SINGLETON_METHOD})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Scope.CLASS, Scope.MODULE})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF, Conditional.ELSIF,
            Conditional.UNLESS_MODIFIER, Conditional.IF_MODIFIER,
            Loop.WHILE_MODIFIER, Loop.UNTIL_MODIFIER,
            Catch.RESCUE_MODIFIER,
            Loop.WHILE, Loop.UNTIL, Loop.FOR,
            Switch.WHEN,
            Catch.RESCUE,
            Conditional.CONDITIONAL,                # ternary x ? a : b
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF, Conditional.UNLESS_MODIFIER,
            Loop.WHILE, Loop.UNTIL, Loop.FOR,
            Switch.CASE, Catch.BEGIN,
            Conditional.CONDITIONAL,
            Node.DO_BLOCK, Node.BLOCK,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({
            Conditional.ELSIF,                      # syntactically inside if
            Switch.WHEN,                            # syntactically inside case
        })

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||", "and", "or"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({
            Literal.INTEGER, Literal.FLOAT,
            Literal.COMPLEX, Literal.RATIONAL,
        })

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Walk method / singleton_method children, skipping def/self/."""
        if node.type not in (Node.METHOD, Node.SINGLETON_METHOD):
            return super().extract_name(node, content)
        saw_def = False
        saw_self = False
        saw_dot = False
        for child in node.children:
            ctype = child.type
            if ctype == "def":
                saw_def = True
                continue
            if not saw_def:
                continue
            if ctype == "self" and not saw_self:
                saw_self = True
                continue
            if ctype == "." and saw_self and not saw_dot:
                saw_dot = True
                continue
            if ctype in (Identifier.IDENTIFIER, Identifier.OPERATOR):
                return content[child.start_byte:child.end_byte].decode(
                    "utf-8", errors="replace",
                ).strip()
        return "<anonymous>"
