"""Ruby grammar — classes + modules + methods.

Tree-sitter-ruby uses ``method`` and ``singleton_method`` node types,
positional naming (no ``name`` field). Overrides ``extract_name`` to
skip ``def``/``self``/``.`` tokens.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Node
from ..multipurpose import MultiPurpose


class Ruby(MultiPurpose):
    id: ClassVar[str] = "ruby"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Node.METHOD, Node.SINGLETON_METHOD})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Node.CLASS, Node.MODULE})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF, Node.ELSIF,
            Node.UNLESS_MODIFIER, Node.IF_MODIFIER,
            Node.WHILE_MODIFIER, Node.UNTIL_MODIFIER,
            Node.RESCUE_MODIFIER,
            Node.WHILE, Node.UNTIL, Node.FOR,
            Node.WHEN,
            Node.RESCUE,
            Node.CONDITIONAL,               # ternary x ? a : b
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Node.IF, Node.UNLESS_MODIFIER,
            Node.WHILE, Node.UNTIL, Node.FOR,
            Node.CASE, Node.BEGIN,
            Node.CONDITIONAL,
            Node.DO_BLOCK, Node.BLOCK,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({
            Node.ELSIF,                     # syntactically inside if
            Node.WHEN,                      # syntactically inside case
        })

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Node.BINARY

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||", "and", "or"})

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
            if ctype in (Node.IDENTIFIER, Node.OPERATOR):
                return content[child.start_byte:child.end_byte].decode(
                    "utf-8", errors="replace",
                ).strip()
        return "<anonymous>"
