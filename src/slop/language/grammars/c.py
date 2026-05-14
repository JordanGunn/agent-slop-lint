"""C grammar — procedural; no classes.

Overrides ``extract_name`` to walk the declarator chain
(``function_declarator → identifier``), which tree-sitter-c uses
instead of a ``name`` field.
"""
from __future__ import annotations

from typing import Any, ClassVar

# Local alias so the ast.Callable enum doesn't shadow typing.Callable
# in this module — Callable members are only used inside method bodies.
from ..ast import Callable as Node
from ..ast import Block, Conditional, Identifier, Literal, Loop, Operator, Switch, Wrapper
from ..procedural import Procedural


class C(Procedural):
    id: ClassVar[str] = "c"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Node.FUNCTION_DEFINITION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.CASE_STATEMENT,                  # both `case X:` and `default:`
            Conditional.CONDITIONAL_EXPRESSION,     # ternary `?:`
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_STATEMENT,                # container for case_statement
            Conditional.CONDITIONAL_EXPRESSION,
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
    def if_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.IF_STATEMENT})

    @classmethod
    def else_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.ELSE_CLAUSE})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({
            Loop.FOR_STATEMENT, Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
        })

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_STATEMENT})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        # Both `case X:` and `default:` emit as case_statement.
        return frozenset({Switch.CASE_STATEMENT})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({Block.COMPOUND_STATEMENT})

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        # C wraps cases inside the switch's compound_statement.
        return frozenset({Block.COMPOUND_STATEMENT})

    @classmethod
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        # C encodes types in declarations rather than annotation nodes:
        # ``void *raw`` splits as ``type: primitive_type "void"`` plus
        # ``declarator: pointer_declarator``. Capturing the whole
        # parameter_declaration text and pattern-matching on ``void *``
        # is the substrate-aligned approach. Return-type pointer-ness
        # lives in the function-definition declarator chain; that
        # path is not covered here.
        return (
            ("(parameter_declaration) @annotation", "param"),
        )

    @classmethod
    def is_escape_hatch_text(cls, text: str) -> bool:
        # ``void *`` (with or without space) is C's universal escape
        # hatch; any pointer-to-void parameter defeats the type checker.
        cleaned = text.replace("\n", " ")
        return "void *" in cleaned or "void*" in cleaned

    @classmethod
    def call_node_types(cls) -> frozenset[str]:
        return frozenset({"call_expression"})

    @classmethod
    def extract_callee_name(cls, call_node: Any, content: bytes) -> str | None:
        fn = call_node.child_by_field_name("function")
        if fn is not None and fn.type == "identifier":
            return content[fn.start_byte:fn.end_byte].decode("utf-8", errors="replace")
        return None

    @classmethod
    def trivial_callees(cls) -> frozenset[str]:
        return frozenset({
            "malloc", "calloc", "realloc", "free", "alloca",
            "memcpy", "memmove", "memset", "memcmp",
            "strlen", "strcpy", "strncpy", "strcat", "strncat",
            "strcmp", "strncmp", "strdup", "strchr", "strrchr",
            "strstr", "strtok", "strerror",
            "printf", "fprintf", "sprintf", "snprintf", "vprintf",
            "scanf", "fscanf", "sscanf",
            "fopen", "fclose", "fread", "fwrite", "fseek", "ftell",
            "fgets", "fputs", "fgetc", "fputc", "feof", "fflush", "ferror",
            "atoi", "atol", "atoll", "atof",
            "abort", "exit", "_exit", "atexit",
            "getenv", "setenv", "unsetenv",
            "assert", "perror", "errno",
        })

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            (
                "(preproc_include path: (string_literal (string_content) @module))",
                "include_local",
            ),
            (
                "(preproc_include path: (system_lib_string) @module)",
                "include_system",
            ),
        )

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.NUMBER_LITERAL})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if", "else", "while", "do", "for",
            "switch", "case", "default",
            "break", "continue", "return", "goto",
            "sizeof", "typedef",
            "struct", "union", "enum",
            "const", "volatile", "static", "extern", "inline",
            "register", "auto", "restrict", "_Alignof", "_Atomic",
            "=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!",
            "~", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=",
            "&=", "|=", "^=", "<<=", ">>=",
            "++", "--",
            "?", ":", ",", ".", "->",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "field_identifier", "type_identifier",
            "number_literal",
            "string_literal", "char_literal",
            "concatenated_string",
            "true", "false", "null",
        })

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Walk the C declarator chain to the identifier."""
        if node.type != Node.FUNCTION_DEFINITION:
            return super().extract_name(node, content)
        declarator = node.child_by_field_name("declarator")
        for _ in range(6):
            if declarator is None:
                return "<anonymous>"
            if declarator.type == Wrapper.FUNCTION_DECLARATOR:
                inner = declarator.child_by_field_name("declarator")
                if inner is not None and inner.type == Identifier.IDENTIFIER:
                    return content[inner.start_byte:inner.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                return "<anonymous>"
            if declarator.type in (
                Wrapper.POINTER_DECLARATOR, Wrapper.PARENTHESIZED_DECLARATOR,
            ):
                declarator = declarator.child_by_field_name("declarator")
                continue
            break
        return "<anonymous>"
