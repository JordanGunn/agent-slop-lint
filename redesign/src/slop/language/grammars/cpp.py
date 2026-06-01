"""C++ grammar — classes/structs + free functions + namespaces."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigms import MultiPurpose


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
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        return (("(parameter_declaration) @annotation", "param"),)

    @classmethod
    def is_dynamic_type(cls, text: str) -> bool:
        cleaned = text.replace("\n", " ")
        return "void *" in cleaned or "void*" in cleaned or "std::any" in cleaned

    @classmethod
    def call_node_types(cls) -> frozenset[str]:
        return frozenset({"call_expression"})

    @classmethod
    def extract_callee_name(cls, call_node: Any, content: bytes) -> str | None:
        fn = call_node.child_by_field_name("function")
        if fn is None:
            return None
        if fn.type == "identifier":
            return content[fn.start_byte:fn.end_byte].decode("utf-8", errors="replace")
        if fn.type == "field_expression":
            field = fn.child_by_field_name("field")
            if field is not None and field.type in ("identifier", "field_identifier"):
                return content[field.start_byte:field.end_byte].decode("utf-8", errors="replace")
        if fn.type == "qualified_identifier":
            last = None
            for c in fn.children:
                if c.type == "identifier":
                    last = c
            if last is not None:
                return content[last.start_byte:last.end_byte].decode("utf-8", errors="replace")
        return None

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
    def hidden_mutators(
        cls, fn_node: Any, content: bytes, *, require_type_annotation: bool = True,
    ) -> list[tuple[str, str, int]]:
        del require_type_annotation
        plist = _parameters(fn_node)
        if plist is None:
            return []
        ptr_params, ref_params = _collect_ptr_ref_params(plist, content)
        body = fn_node.child_by_field_name("body") or fn_node
        out: list[tuple[str, str, int]] = []
        if ptr_params:
            out.extend(_walk_pointer_mutations(body, content, ptr_params))
        if ref_params:
            out.extend(_walk_reference_mutations(body, content, ref_params))
        return out

    @classmethod
    def stringly_typed_params(cls, fn_node: Any, content: bytes) -> list[tuple[str, bool]]:
        plist = _parameters(fn_node)
        if plist is None:
            return []
        out: list[tuple[str, bool]] = []
        for param in plist.children:
            if param.type != "parameter_declaration":
                continue
            name = _string_param_name(param, content)
            if name is not None:
                out.append((name, True))
        return out


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


def _collect_ptr_ref_params(plist: Any, content: bytes) -> tuple[set[str], set[str]]:
    pointers: set[str] = set()
    references: set[str] = set()
    for param in plist.children:
        if param.type != "parameter_declaration":
            continue
        has_const = False
        ptr_decl = ref_decl = None
        for child in param.children:
            if child.type == "type_qualifier":
                if content[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip() == "const":
                    has_const = True
            elif child.type == "pointer_declarator":
                ptr_decl = child
            elif child.type == "reference_declarator":
                ref_decl = child
        if has_const:
            continue
        if ptr_decl is not None:
            name = _decl_ident(ptr_decl, content, scan_children=True)
            if name:
                pointers.add(name)
        elif ref_decl is not None:
            name = _decl_ident(ref_decl, content, scan_children=True)
            if name:
                references.add(name)
    return pointers, references


_STRING_TYPE_BY_NODE: dict[str, frozenset[str]] = {
    "primitive_type": frozenset({"char"}),
    "qualified_identifier": frozenset({"std::string", "std::string_view", "std::wstring", "std::wstring_view"}),
    "type_identifier": frozenset({"string", "string_view", "wstring", "wstring_view"}),
}


def _string_param_name(param: Any, content: bytes) -> str | None:
    is_string = False
    ptr_or_ref = None
    for child in param.children:
        if child.type in ("pointer_declarator", "reference_declarator"):
            ptr_or_ref = child
            continue
        accepted = _STRING_TYPE_BY_NODE.get(child.type)
        if accepted is None:
            continue
        if content[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip() in accepted:
            is_string = True
    if not is_string:
        return None
    if ptr_or_ref is not None:
        return _decl_ident(ptr_or_ref, content)
    ident = _identifier_child(param)
    if ident is not None:
        return content[ident.start_byte:ident.end_byte].decode("utf-8", errors="replace")
    return None


def _walk_pointer_mutations(body: Any, content: bytes, params: set[str]) -> list[tuple[str, str, int]]:
    out: list[tuple[str, str, int]] = []
    stack = [body]
    while stack:
        n = stack.pop()
        if n.type == "assignment_expression":
            lhs = n.child_by_field_name("left")
            if lhs is not None:
                hit = _ptr_lhs_param(lhs, content, params)
                if hit is not None:
                    out.append((hit[0], hit[1], n.start_point[0] + 1))
        stack.extend(n.children)
    return out


def _ptr_lhs_param(lhs: Any, content: bytes, params: set[str]) -> tuple[str, str] | None:
    if lhs.type == "pointer_expression":
        for child in lhs.children:
            if child.type == "identifier":
                name = content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                if name in params:
                    return (name, "deref-assign")
    elif lhs.type == "field_expression":
        if any(c.type == "->" for c in lhs.children):
            obj = lhs.child_by_field_name("argument") or _identifier_child(lhs)
            if obj is not None and obj.type == "identifier":
                name = content[obj.start_byte:obj.end_byte].decode("utf-8", errors="replace")
                if name in params:
                    return (name, "field-assign")
    elif lhs.type == "subscript_expression":
        arg = lhs.child_by_field_name("argument") or _identifier_child(lhs)
        if arg is not None and arg.type == "identifier":
            name = content[arg.start_byte:arg.end_byte].decode("utf-8", errors="replace")
            if name in params:
                return (name, "subscript-assign")
    return None


def _walk_reference_mutations(body: Any, content: bytes, params: set[str]) -> list[tuple[str, str, int]]:
    out: list[tuple[str, str, int]] = []
    stack = [body]
    while stack:
        n = stack.pop()
        if n.type == "assignment_expression":
            lhs = n.child_by_field_name("left")
            if lhs is not None:
                hit = _ref_lhs_param(lhs, content, params)
                if hit is not None:
                    out.append((hit[0], hit[1], n.start_point[0] + 1))
        stack.extend(n.children)
    return out


def _ref_lhs_param(lhs: Any, content: bytes, params: set[str]) -> tuple[str, str] | None:
    if lhs.type == "identifier":
        name = content[lhs.start_byte:lhs.end_byte].decode("utf-8", errors="replace")
        if name in params:
            return (name, "ref-assign")
    elif lhs.type == "field_expression":
        if any(c.type == "." for c in lhs.children):
            obj = lhs.child_by_field_name("argument") or _identifier_child(lhs)
            if obj is not None and obj.type == "identifier":
                name = content[obj.start_byte:obj.end_byte].decode("utf-8", errors="replace")
                if name in params:
                    return (name, "field-assign")
    return None
