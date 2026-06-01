"""C grammar — procedural; no classes. extract_name walks the declarator chain."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import Procedural


class C(Procedural):
    id: ClassVar[str] = "c"

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
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        return (("(parameter_declaration) @annotation", "param"),)

    @classmethod
    def is_dynamic_type(cls, text: str) -> bool:
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
    def parameter_mutations(cls, fn_node: Any, content: bytes) -> list[tuple[str, str, int]]:
        declarator = fn_node.child_by_field_name("declarator")
        while declarator is not None and declarator.type == "pointer_declarator":
            declarator = declarator.child_by_field_name("declarator")
        if declarator is None or declarator.type != "function_declarator":
            return []
        plist = declarator.child_by_field_name("parameters")
        if plist is None:
            return []
        ptr_params = {n for p in plist.children if (n := _ptr_param_name(p, content)) is not None}
        if not ptr_params:
            return []
        body = fn_node.child_by_field_name("body") or fn_node
        out: list[tuple[str, str, int]] = []
        stack = [body]
        while stack:
            n = stack.pop()
            if n.type == "assignment_expression":
                lhs = n.child_by_field_name("left")
                if lhs is not None:
                    hit = _c_lhs_param(lhs, content, ptr_params)
                    if hit is not None:
                        out.append((hit[0], hit[1], n.start_point[0] + 1))
            stack.extend(n.children)
        return out

    @classmethod
    def string_annotated_parameters(cls, fn_node: Any, content: bytes) -> list[tuple[str, bool]]:
        declarator = fn_node.child_by_field_name("declarator")
        for _ in range(6):
            if declarator is None or declarator.type == "function_declarator":
                break
            declarator = declarator.child_by_field_name("declarator")
        if declarator is None or declarator.type != "function_declarator":
            return []
        plist = declarator.child_by_field_name("parameters")
        if plist is None:
            return []
        return [(n, True) for p in plist.children if (n := _char_ptr_param_name(p, content)) is not None]


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


def _ptr_param_name(param: Any, content: bytes) -> str | None:
    if param.type != "parameter_declaration":
        return None
    has_const = False
    ptr_decl = None
    for child in param.children:
        if child.type == "type_qualifier":
            if content[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip() == "const":
                has_const = True
        elif child.type == "pointer_declarator":
            ptr_decl = child
    if has_const or ptr_decl is None:
        return None
    return _decl_ident(ptr_decl, content)


def _char_ptr_param_name(param: Any, content: bytes) -> str | None:
    if param.type != "parameter_declaration":
        return None
    is_char = False
    ptr_decl = None
    for child in param.children:
        if child.type == "primitive_type":
            if content[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip() == "char":
                is_char = True
        elif child.type == "pointer_declarator":
            ptr_decl = child
    if not is_char or ptr_decl is None:
        return None
    return _decl_ident(ptr_decl, content)


def _ident_child(node: Any) -> Any | None:
    for c in node.children:
        if c.type == "identifier":
            return c
    return None


def _c_lhs_param(lhs: Any, content: bytes, params: set[str]) -> tuple[str, str] | None:
    if lhs.type == "pointer_expression":
        for child in lhs.children:
            if child.type == "identifier":
                name = content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                if name in params:
                    return (name, "deref-assign")
        return None
    if lhs.type == "field_expression":
        if not any(c.type == "->" for c in lhs.children):
            return None
        obj = lhs.child_by_field_name("argument") or _ident_child(lhs)
        if obj is not None and obj.type == "identifier":
            name = content[obj.start_byte:obj.end_byte].decode("utf-8", errors="replace")
            if name in params:
                return (name, "field-assign")
        return None
    if lhs.type == "subscript_expression":
        arg = lhs.child_by_field_name("argument") or _ident_child(lhs)
        if arg is not None and arg.type == "identifier":
            name = content[arg.start_byte:arg.end_byte].decode("utf-8", errors="replace")
            if name in params:
                return (name, "subscript-assign")
    return None
