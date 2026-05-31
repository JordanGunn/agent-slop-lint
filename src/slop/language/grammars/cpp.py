"""C++ grammar — classes + free functions + namespaces.

Overrides ``extract_name`` to handle the declarator chain
(``function_declarator → identifier``), qualified identifiers
(out-of-line methods), operator overloads, and destructors.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Callable as Node
from ..ast import Block, Catch, Conditional, Identifier, Literal, Loop, Operator, Scope, Switch, Wrapper
from ..multipurpose import MultiPurpose


class Cpp(MultiPurpose):
    id: ClassVar[str] = "cpp"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Node.FUNCTION_DEFINITION, Node.LAMBDA_EXPRESSION})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Scope.CLASS_SPECIFIER, Scope.STRUCT_SPECIFIER})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({
            Identifier.IDENTIFIER, Identifier.FIELD_IDENTIFIER, Identifier.TYPE_IDENTIFIER,
        })

    @classmethod
    def methods(cls) -> frozenset[str]:
        # Lambdas aren't methods.
        return frozenset({Node.FUNCTION_DEFINITION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOR_RANGE_LOOP,  # range-based for
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.CASE_STATEMENT,                    # case X: / default:
            Conditional.CONDITIONAL_EXPRESSION,       # ternary
            Catch.CATCH_CLAUSE,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.FOR_RANGE_LOOP,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
            Switch.SWITCH_STATEMENT,
            Conditional.CONDITIONAL_EXPRESSION,
            Catch.TRY_STATEMENT,                      # container for catch_clause
            Catch.CATCH_CLAUSE,
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
    def definition_unwrap_types(cls) -> frozenset[str]:
        return frozenset({Wrapper.TEMPLATE_DECLARATION})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({
            Loop.FOR_STATEMENT, Loop.FOR_RANGE_LOOP,
            Loop.WHILE_STATEMENT, Loop.DO_STATEMENT,
        })

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.SWITCH_STATEMENT})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.CASE_STATEMENT})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({Block.COMPOUND_STATEMENT})

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        return frozenset({Block.COMPOUND_STATEMENT})

    @classmethod
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        # Same approach as C — parameter_declaration captures the
        # whole parameter; ``is_escape_hatch_text`` pattern-matches.
        # C++ adds ``std::any`` (C++17) on top of C's ``void *``.
        return (
            ("(parameter_declaration) @annotation", "param"),
        )

    @classmethod
    def is_escape_hatch_text(cls, text: str) -> bool:
        cleaned = text.replace("\n", " ")
        return (
            "void *" in cleaned
            or "void*" in cleaned
            or "std::any" in cleaned
        )

    @classmethod
    def hidden_mutators(
        cls, fn_node: Any, content: bytes,
        *,
        require_type_annotation: bool = True,
    ) -> list[tuple[str, str, int]]:
        del require_type_annotation
        plist = _parameters(fn_node)
        if plist is None:
            return []
        ptr_params, ref_params = _collect_ptr_ref_params(plist, content)
        body = fn_node.child_by_field_name("body") or fn_node
        out: list[tuple[str, str, int]] = []
        # Pointer-mutation shapes (same as C) for ptr_params.
        if ptr_params:
            out.extend(_cpp_walk_pointer_mutations(body, content, ptr_params))
        # Reference-mutation shapes for ref_params: ``p = ...`` (direct
        # assignment to a non-const reference) and ``p.field = ...``.
        if ref_params:
            out.extend(_cpp_walk_reference_mutations(body, content, ref_params))
        return out

    @classmethod
    def stringly_typed_params(
        cls, fn_node: Any, content: bytes,
    ) -> list[tuple[str, bool]]:
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
    def trivial_callees(cls) -> frozenset[str]:
        # Inherits the C stdlib filter (C/C++ usually mix) plus the
        # most common std:: free functions and container methods that
        # otherwise show up in nearly every body.
        from .c import C as _C
        return _C.trivial_callees() | frozenset({
            "make_unique", "make_shared", "move", "forward",
            "begin", "end", "cbegin", "cend", "rbegin", "rend",
            "size", "empty", "front", "back", "push_back", "pop_back",
            "emplace", "emplace_back", "insert", "erase", "find", "count",
            "data", "clear", "reserve", "resize",
            "to_string", "stoi", "stol", "stof", "stod",
        })

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        # tree-sitter-cpp inherits C's preprocessor node types.
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
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        """C++ has no ``abstract`` keyword — abstractness is determined by whether the class declares any pure-virtual method.

        A pure-virtual method is a field_declaration containing a
        ``function_declarator`` followed by ``= 0`` (the ``number_literal``
        ``0`` appears as a direct child of the field_declaration in
        tree-sitter-cpp's emission). Structs are always concrete (C++
        structs are technically classes too but the abstract pattern
        is almost never used with struct keyword).
        """
        del content
        ntype = node.type
        if ntype == Scope.STRUCT_SPECIFIER:
            return False
        if ntype == Scope.CLASS_SPECIFIER:
            body = node.child_by_field_name("body")
            if body is None:
                return False
            for member in body.children:
                if member.type != "field_declaration":
                    continue
                has_func_decl = False
                has_zero_literal = False
                for c in member.children:
                    if c.type == "function_declarator":
                        has_func_decl = True
                    elif c.type == "number_literal":
                        has_zero_literal = True
                if has_func_decl and has_zero_literal:
                    return True
            return False
        return None

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.NUMBER_LITERAL})

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """C++: ``base_class_clause`` direct child holds parent type names.

        ``class Dog : public Animal, private Pet`` → ['Animal', 'Pet'].
        Qualified names (``std::exception``) keep only the last segment.
        """
        out: list[str] = []
        for child in node.children:
            if child.type != "base_class_clause":
                continue
            for sub in child.children:
                if sub.type == "type_identifier":
                    out.append(content[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace"))
                elif sub.type == "qualified_identifier":
                    last = None
                    for c in sub.children:
                        if c.type in ("identifier", "type_identifier"):
                            last = c
                    if last is not None:
                        out.append(content[last.start_byte:last.end_byte].decode("utf-8", errors="replace"))
        return out

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            # C keywords (carry over)
            "if", "else", "while", "do", "for",
            "switch", "case", "default",
            "break", "continue", "return", "goto",
            "sizeof", "typedef",
            "struct", "union", "enum",
            "const", "volatile", "static", "extern", "inline",
            "register", "auto", "restrict",
            # C++ keywords
            "class", "namespace", "template", "typename",
            "public", "private", "protected", "virtual",
            "override", "final", "explicit", "friend",
            "new", "delete", "this", "operator",
            "try", "catch", "throw", "noexcept",
            "using", "nullptr",
            "constexpr", "consteval", "constinit",
            "decltype", "static_cast", "dynamic_cast",
            "reinterpret_cast", "const_cast",
            "co_await", "co_yield", "co_return",
            "=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=", "<=>",
            "&&", "||", "!",
            "~", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=",
            "&=", "|=", "^=", "<<=", ">>=",
            "++", "--",
            "?", ":", ",", ".", "->", "::",
            "->*", ".*",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "field_identifier", "type_identifier",
            "namespace_identifier", "template_type",
            "number_literal",
            "string_literal", "char_literal", "raw_string_literal",
            "concatenated_string", "user_defined_literal",
            "true", "false", "null", "nullptr",
            "this",
        })

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Walk the C++ declarator chain to find the function name.

        Handles plain functions, pointer/reference returns, in-class
        methods, out-of-line methods (qualified_identifier), operator
        overloads, destructors.
        """
        if node.type == Node.LAMBDA_EXPRESSION:
            return "<lambda>"
        if node.type != Node.FUNCTION_DEFINITION:
            # Fall back to default for non-function nodes (class_specifier etc.).
            return super().extract_name(node, content)
        fdecl = _function_declarator(node)
        if fdecl is None:
            return "<anonymous>"
        inner = fdecl.child_by_field_name("declarator")
        if inner is None:
            return "<anonymous>"
        return _name_from_declarator_inner(inner, content)


def _function_declarator(fn_node: Any) -> Any | None:
    """Unwrap pointer/reference/parenthesized declarators to the function_declarator.

    C++ wraps the function_declarator when the return type is a pointer
    or reference (``int* f(...)`` → pointer_declarator → function_declarator).
    Returns the function_declarator node, or None if the chain doesn't reach
    one within a bounded number of hops.
    """
    declarator = fn_node.child_by_field_name("declarator")
    for _ in range(8):
        if declarator is None:
            return None
        if declarator.type == "function_declarator":
            return declarator
        if declarator.type in (
            "pointer_declarator", "reference_declarator",
            "parenthesized_declarator",
        ):
            declarator = declarator.child_by_field_name("declarator")
            continue
        return None
    return None


def _parameters(fn_node: Any) -> Any | None:
    """Return the parameter_list node of a function definition, or None."""
    fdecl = _function_declarator(fn_node)
    if fdecl is None:
        return None
    return fdecl.child_by_field_name("parameters")


def _declarator_identifier(
    decl: Any, content: bytes, *, scan_children: bool = False,
) -> str | None:
    """Walk a pointer/reference declarator chain to its inner identifier name.

    ``scan_children`` mirrors the original hidden_mutators behavior of
    falling back to a direct identifier child when ``declarator`` is absent;
    stringly_typed_params left untouched (passes False).
    """
    cur = decl
    for _ in range(4):
        if cur is None:
            return None
        inner = cur.child_by_field_name("declarator")
        if inner is None and scan_children:
            for c in cur.children:
                if c.type == "identifier":
                    inner = c
                    break
        if inner is None:
            return None
        if inner.type == "identifier":
            return content[inner.start_byte:inner.end_byte].decode(
                "utf-8", errors="replace",
            )
        cur = inner
    return None


def _collect_ptr_ref_params(
    plist: Any, content: bytes,
) -> tuple[set[str], set[str]]:
    """Partition a parameter_list into non-const pointer and reference names."""
    pointers: set[str] = set()
    references: set[str] = set()
    for param in plist.children:
        if param.type != "parameter_declaration":
            continue
        has_const = False
        ptr_decl = None
        ref_decl = None
        for child in param.children:
            ctype = child.type
            if ctype == "type_qualifier":
                qtext = content[child.start_byte:child.end_byte].decode(
                    "utf-8", errors="replace",
                ).strip()
                if qtext == "const":
                    has_const = True
            elif ctype == "pointer_declarator":
                ptr_decl = child
            elif ctype == "reference_declarator":
                ref_decl = child
        if has_const:
            continue
        target_decl = ptr_decl or ref_decl
        if target_decl is None:
            continue
        name = _declarator_identifier(target_decl, content, scan_children=True)
        if name is None:
            continue
        if target_decl is ptr_decl:
            pointers.add(name)
        else:
            references.add(name)
    return pointers, references


_STRING_QUALIFIED = frozenset({
    "std::string", "std::string_view", "std::wstring", "std::wstring_view",
})
_STRING_TYPE_ID = frozenset({"string", "string_view", "wstring", "wstring_view"})


def _string_param_name(param: Any, content: bytes) -> str | None:
    """Return the name of a string-typed parameter, or None if not a string.

    Recognises ``char`` (with a pointer declarator), ``std::string`` family
    (qualified_identifier), and the unqualified ``string`` family
    (type_identifier under a ``using namespace std``).
    """
    is_string = False
    ptr_or_ref = None
    for child in param.children:
        ctype = child.type
        if ctype == "primitive_type":
            text = content[child.start_byte:child.end_byte].decode(
                "utf-8", errors="replace",
            ).strip()
            if text == "char":
                is_string = True
        elif ctype in ("pointer_declarator", "reference_declarator"):
            ptr_or_ref = child
        elif ctype == "qualified_identifier":
            text = content[child.start_byte:child.end_byte].decode(
                "utf-8", errors="replace",
            ).strip()
            if text in _STRING_QUALIFIED:
                is_string = True
        elif ctype == "type_identifier":
            text = content[child.start_byte:child.end_byte].decode(
                "utf-8", errors="replace",
            ).strip()
            if text in _STRING_TYPE_ID:
                is_string = True
    if not is_string:
        return None
    if ptr_or_ref is not None:
        return _declarator_identifier(ptr_or_ref, content)
    for child in param.children:
        if child.type == "identifier":
            return content[child.start_byte:child.end_byte].decode(
                "utf-8", errors="replace",
            )
    return None


def _name_from_declarator_inner(inner: Any, content: bytes) -> str:
    """Resolve a function name from the function_declarator's inner declarator.

    Handles plain/field identifiers, out-of-line qualified names, operator
    overloads, and destructors; returns ``<anonymous>`` for anything else.
    """
    itype = inner.type
    if itype in (Identifier.IDENTIFIER, Identifier.FIELD_IDENTIFIER):
        return content[inner.start_byte:inner.end_byte].decode(
            "utf-8", errors="replace",
        )
    if itype == Identifier.QUALIFIED_IDENTIFIER:
        for c in reversed(inner.children):
            if c.type == Identifier.IDENTIFIER:
                return content[c.start_byte:c.end_byte].decode(
                    "utf-8", errors="replace",
                )
        return "<anonymous>"
    if itype == Identifier.OPERATOR_NAME:
        for c in inner.children:
            if c.type != Identifier.OPERATOR:
                return content[c.start_byte:c.end_byte].decode(
                    "utf-8", errors="replace",
                ).strip()
        return "<anonymous>"
    if itype == Identifier.DESTRUCTOR_NAME:
        for c in inner.children:
            if c.type == Identifier.IDENTIFIER:
                return "~" + content[c.start_byte:c.end_byte].decode(
                    "utf-8", errors="replace",
                )
        return "<anonymous>"
    return "<anonymous>"


def _cpp_walk_pointer_mutations(
    body: Any, content: bytes, params: set[str],
) -> list[tuple[str, str, int]]:
    # Shares the C pointer-mutation walker.
    from .c import _c_walk_pointer_mutations
    return _c_walk_pointer_mutations(body, content, params)


def _cpp_walk_reference_mutations(
    body: Any, content: bytes, params: set[str],
) -> list[tuple[str, str, int]]:
    """Find direct or field assignments through C++ reference parameters."""
    out: list[tuple[str, str, int]] = []
    stack = [body]
    while stack:
        n = stack.pop()
        if n.type == "assignment_expression":
            lhs = n.child_by_field_name("left")
            if lhs is not None:
                hit = _reference_lhs_param(lhs, content, params)
                if hit is not None:
                    name, kind = hit
                    out.append((name, kind, n.start_point[0] + 1))
        stack.extend(n.children)
    return out


def _reference_lhs_param(
    lhs: Any, content: bytes, params: set[str],
) -> tuple[str, str] | None:
    """Classify an assignment LHS as a reference-param mutation, or None.

    ``r = ...`` (direct assignment to a non-const reference) → ``ref-assign``;
    ``r.field = ...`` → ``ref-field-assign``. Mirrors C's ``_c_lhs_param``.
    """
    ltype = lhs.type
    if ltype == "identifier":
        name = content[lhs.start_byte:lhs.end_byte].decode("utf-8", errors="replace")
        if name in params:
            return (name, "ref-assign")
        return None
    if ltype == "field_expression":
        obj = lhs.child_by_field_name("argument")
        if obj is None:
            for c in lhs.children:
                if c.type == "identifier":
                    obj = c
                    break
        if obj is not None and obj.type == "identifier":
            name = content[obj.start_byte:obj.end_byte].decode("utf-8", errors="replace")
            if name in params:
                return (name, "ref-field-assign")
    return None
