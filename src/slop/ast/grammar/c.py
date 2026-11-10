"""C grammar — struct/union/enum definitions are class-like scopes; functions are free
callables. extract_name walks the declarator chain, and names an anonymous
``typedef struct {...} Name;`` from its typedef."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import MultiPurpose


class C(MultiPurpose):
    id: ClassVar[str] = "c"

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"struct_specifier", "union_specifier", "enum_specifier"})

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset()

    @classmethod
    def is_class_definition(cls, node: Any) -> bool:
        # A specifier with a body defines the type; without one it is a forward
        # declaration or a reference (``struct Node *head;``, ``struct Node *next;``).
        return node.child_by_field_name("body") is not None

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_definition"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "while_statement",
                          "do_statement", "case_statement", "conditional_expression"})

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "while_statement",
                          "do_statement", "switch_statement", "conditional_expression"})

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"case_statement"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def try_nodes(cls) -> frozenset[str]:
        return frozenset()

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        return frozenset()

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({"for_statement", "while_statement", "do_statement"})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({"switch_statement"})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({"case_statement"})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({"compound_statement"})

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        return frozenset({"compound_statement"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"number_literal"})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if", "else", "while", "do", "for", "switch", "case", "default",
            "break", "continue", "return", "goto", "sizeof", "typedef",
            "struct", "union", "enum", "const", "volatile", "static", "extern",
            "inline", "register", "auto", "restrict",
            "=", "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "~", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=",
            "++", "--", "?", ":", ",", ".", "->",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "field_identifier", "type_identifier", "number_literal",
            "string_literal", "char_literal", "concatenated_string", "true", "false", "null",
        })

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(preproc_include path: (string_literal (string_content) @module))", "include_local"),
            ("(preproc_include path: (system_lib_string) @module)", "include_system"),
        )

    @classmethod
    def call_node_types(cls) -> frozenset[str]:
        return frozenset({"call_expression"})

    @classmethod
    def language_builtins(cls) -> frozenset[str]:
        return frozenset({
            "malloc", "calloc", "realloc", "free", "alloca", "memcpy", "memmove",
            "memset", "memcmp", "strlen", "strcpy", "strncpy", "strcat", "strncat",
            "strcmp", "strncmp", "strdup", "strchr", "strrchr", "strstr", "strtok",
            "strerror", "printf", "fprintf", "sprintf", "snprintf", "vprintf",
            "scanf", "fscanf", "sscanf", "fopen", "fclose", "fread", "fwrite",
            "fseek", "ftell", "fgets", "fputs", "fgetc", "fputc", "feof", "fflush",
            "ferror", "atoi", "atol", "atoll", "atof", "abort", "exit", "_exit",
            "atexit", "getenv", "setenv", "unsetenv", "assert", "perror", "errno",
        })

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        if node.type in cls.classes():
            return _type_name(node, content)
        if node.type != "function_definition":
            return super().extract_name(node, content)
        declarator = node.child_by_field_name("declarator")
        for _ in range(6):
            if declarator is None:
                return "<anonymous>"
            if declarator.type == "function_declarator":
                inner = declarator.child_by_field_name("declarator")
                if inner is not None and inner.type == "identifier":
                    return content[inner.start_byte:inner.end_byte].decode("utf-8", errors="replace")
                return "<anonymous>"
            if declarator.type in ("pointer_declarator", "parenthesized_declarator"):
                declarator = declarator.child_by_field_name("declarator")
                continue
            break
        return "<anonymous>"

    @classmethod
    def extract_parameters(cls, node: Any, content: bytes) -> tuple[tuple[str, str | None], ...]:
        """C params hang off the function declarator; names nest in declarators."""
        from ..paradigm.base import c_style_parameters
        return c_style_parameters(node, content)


def _decl_ident(decl: Any, content: bytes) -> str | None:
    cur = decl
    for _ in range(4):
        if cur is None:
            return None
        inner = cur.child_by_field_name("declarator")
        if inner is None:
            return None
        if inner.type == "identifier":
            return content[inner.start_byte:inner.end_byte].decode("utf-8", errors="replace")
        cur = inner
    return None


def _type_name(node: Any, content: bytes) -> str:
    """A struct/union/enum's tag, else the name of the ``typedef`` that wraps it."""
    name = node.child_by_field_name("name")
    if name is None and node.parent is not None and node.parent.type == "type_definition":
        name = node.parent.child_by_field_name("declarator")
    if name is None or name.type not in ("type_identifier", "identifier"):
        return "<anonymous>"
    return content[name.start_byte:name.end_byte].decode("utf-8", errors="replace")
