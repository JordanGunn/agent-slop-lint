"""C++ grammar — classes/structs + free functions + namespaces."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import MultiPurpose
from ..paradigm.base import MemberAccess, has_keyword
from ..paradigm.heritage import heritage
from .c_family import CFamily


_IDENTIFIER = "identifier"
_UTF8 = "utf-8"


class Cpp(CFamily, MultiPurpose):
    id: ClassVar[str] = "cpp"

    @classmethod
    def class_scope_visible(cls) -> bool:
        return True

    @classmethod
    def member_access(cls) -> tuple[MemberAccess, ...]:
        """``this->x`` and the callee of ``this->m()``."""
        return (MemberAccess("field_expression", "argument", "field"),)

    @classmethod
    def instance_receiver(cls, method: Any, content: bytes) -> str | None:
        """``this``, except in a ``static`` member function, which has no instance."""
        return None if has_keyword(method, content, "storage_class_specifier", "static") else "this"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_definition", "lambda_expression"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_specifier", "struct_specifier", "union_specifier",
                          "enum_specifier"})

    @classmethod
    def is_class_definition(cls, node: Any) -> bool:
        # Only a specifier with a body defines the type; ``class Widget;``,
        # ``struct Node *head;`` and ``struct Node *alt;`` inside a body are references.
        return node.child_by_field_name("body") is not None

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({_IDENTIFIER, "field_identifier", "type_identifier"})

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
    def definition_unwrap_types(cls) -> frozenset[str]:
        return frozenset({"template_declaration"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({"for_statement", "for_range_loop", "while_statement", "do_statement"})

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
            _IDENTIFIER, "field_identifier", "type_identifier", "namespace_identifier",
            "template_type", "number_literal", "string_literal", "char_literal",
            "raw_string_literal", "concatenated_string", "user_defined_literal",
            "true", "false", "null", "nullptr", "this",
        })

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
        return heritage(node, content, ("base_class_clause",))

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        if node.type in cls.classes():
            from ..paradigm.base import type_specifier_name
            return type_specifier_name(node, content)
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
        if c.type == _IDENTIFIER:
            return c
    return None


def _name_from_declarator_inner(inner: Any, content: bytes) -> str:
    itype = inner.type
    if itype in (_IDENTIFIER, "field_identifier"):
        return content[inner.start_byte:inner.end_byte].decode(_UTF8, errors="replace")
    if itype == "qualified_identifier":
        for c in reversed(inner.children):
            if c.type == _IDENTIFIER:
                return content[c.start_byte:c.end_byte].decode(_UTF8, errors="replace")
        return "<anonymous>"
    if itype == "operator_name":
        return content[inner.start_byte:inner.end_byte].decode(_UTF8, errors="replace")
    if itype == "destructor_name":
        return content[inner.start_byte:inner.end_byte].decode(_UTF8, errors="replace")
    return "<anonymous>"


def _is_pure_virtual(member: Any) -> bool:
    if member.type != "field_declaration":
        return False
    has_func = any(c.type == "function_declarator" for c in member.children)
    has_zero = any(c.type == "number_literal" for c in member.children)
    return has_func and has_zero


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
        if inner.type == _IDENTIFIER:
            return content[inner.start_byte:inner.end_byte].decode(_UTF8, errors="replace")
        cur = inner
    return None
