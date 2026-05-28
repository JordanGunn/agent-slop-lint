"""Java grammar — class-only (no free functions; `static` lives in a class)."""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Block, Callable, Catch, Conditional, Literal, Loop, Operator, Scope, Switch
from ..objectoriented import ObjectOriented


class Java(ObjectOriented):
    id: ClassVar[str] = "java"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Callable.METHOD_DECLARATION, Callable.CONSTRUCTOR_DECLARATION})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({
            Scope.CLASS_DECLARATION, Scope.INTERFACE_DECLARATION, Scope.RECORD_DECLARATION,
        })

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.ENHANCED_FOR_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_LABEL,            # case label in classic switch_statement
            Switch.SWITCH_RULE,             # arrow rule in modern switch_expression
            Catch.CATCH_CLAUSE,
            Conditional.TERNARY_EXPRESSION,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.ENHANCED_FOR_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_STATEMENT,        # classic container
            Switch.SWITCH_EXPRESSION,       # Java 14+ container
            Catch.CATCH_CLAUSE,
            Conditional.TERNARY_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_LABEL, Switch.SWITCH_RULE})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({
            Loop.FOR_STATEMENT, Loop.ENHANCED_FOR_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
        })

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        # Both classic switch_statement and Java 14+ switch_expression.
        # The legacy ccx_kernel under-counted switch_expression because
        # it tracked switch_node as a single string; this set fixes that.
        return frozenset({Switch.SWITCH_STATEMENT, Switch.SWITCH_EXPRESSION})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        # switch_label appears inside switch_statement; switch_rule
        # appears inside switch_expression (arrow syntax).
        return frozenset({Switch.SWITCH_LABEL, Switch.SWITCH_RULE})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({Block.BLOCK})

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        return frozenset({Block.SWITCH_BLOCK, Block.SWITCH_BLOCK_STATEMENT_GROUP})

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(import_declaration (scoped_identifier) @module)", "java_import"),
            ("(import_declaration (identifier) @module)", "java_import"),
        )

    @classmethod
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(formal_parameter type: (_) @annotation)", "param"),
            ("(method_declaration type: (_) @annotation)", "return"),
        )

    @classmethod
    def is_escape_hatch_text(cls, text: str) -> bool:
        # Java escape: ``Object``. Generic forms ``Object[]``, ``List<Object>``,
        # ``Map<String, Object>`` all count.
        cleaned = text.strip()
        if cleaned == "Object":
            return True
        # Strip generics and array brackets, then check trailing token.
        tokens = set()
        buf: list[str] = []
        for ch in cleaned:
            if ch.isalnum() or ch == "_":
                buf.append(ch)
            else:
                if buf:
                    tokens.add("".join(buf))
                    buf = []
        if buf:
            tokens.add("".join(buf))
        return "Object" in tokens

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        """Interfaces are abstract; ``abstract class`` is abstract; records and plain classes are concrete."""
        ntype = node.type
        if ntype == Scope.INTERFACE_DECLARATION:
            return True
        if ntype == Scope.RECORD_DECLARATION:
            return False
        if ntype == Scope.CLASS_DECLARATION:
            return _has_modifier(node, content, "abstract")
        return None

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({
            Literal.DECIMAL_INTEGER_LITERAL,
            Literal.DECIMAL_FLOATING_POINT_LITERAL,
            Literal.HEX_INTEGER_LITERAL,
            Literal.OCTAL_INTEGER_LITERAL,
        })

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if", "else", "for", "while", "do", "return",
            "class", "interface", "enum", "extends", "implements",
            "import", "package", "try", "catch", "finally",
            "throw", "throws", "new", "instanceof", "switch",
            "case", "default", "break", "continue",
            "public", "private", "protected", "static", "final",
            "abstract", "synchronized", "volatile",
            "void", "super", "this",
            "=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "~", "&", "|", "^", "<<", ">>", ">>>",
            "+=", "-=", "*=", "/=", "%=",
            "++", "--", "?", "->",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "type_identifier", "field_identifier",
            "decimal_integer_literal", "hex_integer_literal",
            "octal_integer_literal", "binary_integer_literal",
            "decimal_floating_point_literal",
            "string_literal", "string_fragment",
            "character_literal",
            "true", "false", "null",
        })

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """Java: ``superclass`` field for extends + ``interfaces`` for implements."""
        out: list[str] = []
        sc = node.child_by_field_name("superclass")
        if sc is not None:
            for child in sc.children:
                if child.type == "type_identifier":
                    out.append(content[child.start_byte:child.end_byte].decode("utf-8", errors="replace"))
        ifaces = node.child_by_field_name("interfaces")
        if ifaces is not None:
            for child in ifaces.children:
                if child.type == "type_list":
                    for tc in child.children:
                        if tc.type == "type_identifier":
                            out.append(content[tc.start_byte:tc.end_byte].decode("utf-8", errors="replace"))
                elif child.type == "type_identifier":
                    out.append(content[child.start_byte:child.end_byte].decode("utf-8", errors="replace"))
        return out


def _has_modifier(node: Any, content: bytes, keyword: str) -> bool:
    """Scan a ``(modifiers ...)`` child for a bare keyword token.

    Java/C#/TS emit modifiers as direct children of ``modifiers`` —
    e.g. ``(modifiers (public) (abstract))``. Matching by ``node.type``
    handles the common case; matching by text covers grammars that
    expose the keyword as a generic node.
    """
    for child in node.children:
        if child.type != "modifiers":
            continue
        for mod in child.children:
            if mod.type == keyword:
                return True
            text = content[mod.start_byte:mod.end_byte].decode("utf-8", errors="replace").strip()
            if text == keyword:
                return True
    return False
