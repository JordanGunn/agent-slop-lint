"""C# grammar — class-only (no top-level free functions historically)."""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Block, Callable, Catch, Conditional, Literal, Loop, Operator, Scope, Switch
from ..objectoriented import ObjectOriented


class CSharp(ObjectOriented):
    id: ClassVar[str] = "c_sharp"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Callable.METHOD_DECLARATION, Callable.CONSTRUCTOR_DECLARATION,
            Callable.LOCAL_FUNCTION_STATEMENT,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({
            Scope.CLASS_DECLARATION, Scope.INTERFACE_DECLARATION, Scope.STRUCT_DECLARATION,
        })

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOREACH_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_SECTION,
            Catch.CATCH_CLAUSE,
            Conditional.CONDITIONAL_EXPRESSION,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOREACH_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_STATEMENT,
            Catch.CATCH_CLAUSE,
            Conditional.CONDITIONAL_EXPRESSION,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_SECTION})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def if_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.IF_STATEMENT})

    # else_nodes intentionally empty — C# emits `else` as a bare
    # keyword child of if_statement; see bare_else_keyword.

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({
            Loop.FOR_STATEMENT, Loop.FOREACH_STATEMENT,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
        })

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_STATEMENT})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_SECTION})

    @classmethod
    def try_nodes(cls) -> frozenset[str]:
        return frozenset({Catch.TRY_STATEMENT})

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        return frozenset({Catch.CATCH_CLAUSE})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({Block.BLOCK})

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        return frozenset({Block.SWITCH_BODY})

    @classmethod
    def bare_else_keyword(cls) -> str | None:
        return "else"

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(using_directive (identifier) @module)", "csharp_using"),
            ("(using_directive (qualified_name) @module)", "csharp_using"),
        )

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        """Interfaces are abstract; ``abstract class`` is abstract; concrete class / struct otherwise."""
        ntype = node.type
        if ntype == Scope.INTERFACE_DECLARATION:
            return True
        if ntype == Scope.STRUCT_DECLARATION:
            return False
        if ntype == Scope.CLASS_DECLARATION:
            # tree-sitter-c-sharp emits modifiers as a flat ``modifier`` child
            # rather than wrapped in ``(modifiers ...)``.
            for child in node.children:
                if child.type == "modifier":
                    text = content[child.start_byte:child.end_byte].decode(
                        "utf-8", errors="replace",
                    ).strip()
                    if text == "abstract":
                        return True
            return False
        return None

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.INTEGER_LITERAL, Literal.REAL_LITERAL})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if", "else", "for", "foreach", "while", "do", "return",
            "class", "struct", "interface", "enum",
            "using", "namespace", "try", "catch", "finally",
            "throw", "new", "is", "as", "switch", "in",
            "case", "default", "break", "continue",
            "public", "private", "protected", "internal", "static",
            "readonly", "abstract", "virtual", "override", "sealed",
            "async", "await", "void", "this", "base", "var",
            "=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "~", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=",
            "++", "--", "?", "=>", "??",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "type_identifier",
            "integer_literal", "real_literal",
            "string_literal", "verbatim_string_literal",
            "interpolated_string_expression",
            "character_literal",
            "true", "false", "null",
        })

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """C#: ``base_list`` child holds identifier classes + interfaces."""
        out: list[str] = []
        for child in node.children:
            if child.type == "base_list":
                for gc in child.children:
                    if gc.type == "identifier":
                        out.append(content[gc.start_byte:gc.end_byte].decode("utf-8", errors="replace"))
        return out
