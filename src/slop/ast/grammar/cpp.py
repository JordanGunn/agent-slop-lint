"""C++ grammar — classes/structs + free functions + namespaces."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import MultiPurpose


class Cpp(MultiPurpose):
    id: ClassVar[str] = "cpp"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_definition", "lambda_expression"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_specifier", "struct_specifier"})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({"identifier", "field_identifier", "type_identifier"})

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({"function_definition"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "for_range_loop",
                          "while_statement", "do_statement", "case_statement",
                          "conditional_expression", "catch_clause"})

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "for_range_loop",
                          "while_statement", "do_statement", "switch_statement",
                          "conditional_expression", "try_statement", "catch_clause"})

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
    def definition_unwrap_types(cls) -> frozenset[str]:
        return frozenset({"template_declaration"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({"for_statement", "for_range_loop", "while_statement", "do_statement"})

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
            "inline", "register", "auto", "class", "namespace", "template",
            "typename", "public", "private", "protected", "virtual", "override",
            "final", "explicit", "friend", "new", "delete", "this", "operator",
            "try", "catch", "throw", "noexcept", "using", "nullptr", "constexpr",
            "decltype", "static_cast", "dynamic_cast", "reinterpret_cast", "const_cast",
            "=", "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=", "<=>",
            "&&", "||", "!", "~", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=",
            "++", "--", "?", ":", ",", ".", "->", "::", "->*", ".*",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "field_identifier", "type_identifier", "namespace_identifier",
            "template_type", "number_literal", "string_literal", "char_literal",
            "raw_string_literal", "concatenated_string", "user_defined_literal",
            "true", "false", "null", "nullptr", "this",
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
        from .c import C as _C
        return _C.language_builtins() | frozenset({
            "make_unique", "make_shared", "move", "forward", "begin", "end",
            "cbegin", "cend", "rbegin", "rend", "size", "empty", "front", "back",
            "push_back", "pop_back", "emplace", "emplace_back", "insert", "erase",
            "find", "count", "data", "clear", "reserve", "resize",
            "to_string", "stoi", "stol", "stof", "stod",
        })

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        del content
        if node.type == "struct_specifier":
            return False
        if node.type != "class_specifier":
            return None
        body = node.child_by_field_name("body")
        if body is None:
            return False
        return any(_is_pure_virtual(m) for m in body.children)

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        out: list[str] = []
        for child in node.children:
            if child.type == "base_class_clause":
                out.extend(_base_class_names(child, content))
        return out

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        if node.type == "lambda_expression":
            return "<lambda>"
        if node.type != "function_definition":
            return super().extract_name(node, content)
        fdecl = _function_declarator(node)
        if fdecl is None:
            return "<anonymous>"
        inner = fdecl.child_by_field_name("declarator")
        if inner is None:
            return "<anonymous>"
        return _name_from_declarator_inner(inner, content)

    @classmethod
    def extract_parameters(cls, node: Any, content: bytes) -> tuple[tuple[str, str | None], ...]:
        """C++ params hang off the function declarator; names nest in declarators."""
        from ..paradigm.base import c_style_parameters
        return c_style_parameters(node, content)


# ---- declarator / name helpers -------------------------------------------

def _function_declarator(fn_node: Any) -> Any | None:
    declarator = fn_node.child_by_field_name("declarator")
    for _ in range(8):
        if declarator is None:
            return None
        if declarator.type == "function_declarator":
            return declarator
        if declarator.type in ("pointer_declarator", "reference_declarator", "parenthesized_declarator"):
            declarator = declarator.child_by_field_name("declarator")
            continue
        return None
    return None


def _parameters(fn_node: Any) -> Any | None:
    fdecl = _function_declarator(fn_node)
    return fdecl.child_by_field_name("parameters") if fdecl is not None else None


def _identifier_child(node: Any) -> Any | None:
    for c in node.children:
        if c.type == "identifier":
            return c
    return None


def _name_from_declarator_inner(inner: Any, content: bytes) -> str:
    itype = inner.type
    if itype in ("identifier", "field_identifier"):
        return content[inner.start_byte:inner.end_byte].decode("utf-8", errors="replace")
    if itype == "qualified_identifier":
        for c in reversed(inner.children):
            if c.type == "identifier":
                return content[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
        return "<anonymous>"
    if itype == "operator_name":
        return content[inner.start_byte:inner.end_byte].decode("utf-8", errors="replace")
    if itype == "destructor_name":
        return content[inner.start_byte:inner.end_byte].decode("utf-8", errors="replace")
    return "<anonymous>"


def _is_pure_virtual(member: Any) -> bool:
    if member.type != "field_declaration":
        return False
    has_func = any(c.type == "function_declarator" for c in member.children)
    has_zero = any(c.type == "number_literal" for c in member.children)
    return has_func and has_zero


def _base_class_names(clause: Any, content: bytes) -> list[str]:
    names: list[str] = []
    for sub in clause.children:
        if sub.type == "type_identifier":
            names.append(content[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace"))
        elif sub.type == "qualified_identifier":
            last = None
            for c in sub.children:
                if c.type in ("identifier", "type_identifier"):
                    last = c
            if last is not None:
                names.append(content[last.start_byte:last.end_byte].decode("utf-8", errors="replace"))
    return names


# ---- pointer/reference param + mutation helpers --------------------------

def _decl_ident(decl: Any, content: bytes, *, scan_children: bool = False) -> str | None:
    cur = decl
    for _ in range(4):
        if cur is None:
            return None
        inner = cur.child_by_field_name("declarator")
        if inner is None and scan_children:
            inner = _identifier_child(cur)
        if inner is None:
            return None
        if inner.type == "identifier":
            return content[inner.start_byte:inner.end_byte].decode("utf-8", errors="replace")
        cur = inner
    return None
