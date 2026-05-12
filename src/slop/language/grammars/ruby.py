"""Ruby grammar — classes + modules + methods.

Tree-sitter-ruby uses ``method`` and ``singleton_method`` node types,
positional naming (no ``name`` field). Overrides ``extract_name`` to
skip ``def``/``self``/``.`` tokens.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..multipurpose import MultiPurpose


class Ruby(MultiPurpose):
    id: ClassVar[str] = "ruby"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"method", "singleton_method"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class", "module"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if", "elsif",
            "unless_modifier", "if_modifier",
            "while_modifier", "until_modifier",
            "rescue_modifier",
            "while", "until", "for",
            "when",
            "rescue",
            "conditional",              # ternary x ? a : b
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if", "unless_modifier",
            "while", "until", "for",
            "case", "begin",
            "conditional",
            "do_block", "block",
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({
            "elsif",                    # syntactically inside if
            "when",                     # syntactically inside case
        })

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||", "and", "or"})

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Walk method / singleton_method children, skipping def/self/."""
        if node.type not in ("method", "singleton_method"):
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
            if ctype in ("identifier", "operator"):
                return content[child.start_byte:child.end_byte].decode(
                    "utf-8", errors="replace",
                ).strip()
        return "<anonymous>"
