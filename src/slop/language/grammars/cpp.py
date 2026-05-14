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
    def if_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.IF_STATEMENT})

    @classmethod
    def else_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.ELSE_CLAUSE})

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
    def try_nodes(cls) -> frozenset[str]:
        return frozenset({Catch.TRY_STATEMENT})

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        return frozenset({Catch.CATCH_CLAUSE})

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
    def stringly_typed_params(
        cls, fn_node: Any, content: bytes,
    ) -> list[tuple[str, bool]]:
        declarator = fn_node.child_by_field_name("declarator")
        for _ in range(8):
            if declarator is None or declarator.type == "function_declarator":
                break
            if declarator.type in (
                "pointer_declarator", "reference_declarator",
                "parenthesized_declarator",
            ):
                declarator = declarator.child_by_field_name("declarator")
                continue
            break
        if declarator is None or declarator.type != "function_declarator":
            return []
        plist = declarator.child_by_field_name("parameters")
        if plist is None:
            return []

        out: list[tuple[str, bool]] = []
        for param in plist.children:
            if param.type != "parameter_declaration":
                continue
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
                    if text in (
                        "std::string", "std::string_view",
                        "std::wstring", "std::wstring_view",
                    ):
                        is_string = True
                elif ctype == "type_identifier":
                    text = content[child.start_byte:child.end_byte].decode(
                        "utf-8", errors="replace",
                    ).strip()
                    if text in ("string", "string_view", "wstring", "wstring_view"):
                        is_string = True
            if not is_string:
                continue

            name: str | None = None
            if ptr_or_ref is not None:
                cur = ptr_or_ref
                for _ in range(4):
                    if cur is None:
                        break
                    inner = cur.child_by_field_name("declarator")
                    if inner is None:
                        break
                    if inner.type == "identifier":
                        name = content[inner.start_byte:inner.end_byte].decode(
                            "utf-8", errors="replace",
                        )
                        break
                    cur = inner
            else:
                for child in param.children:
                    if child.type == "identifier":
                        name = content[child.start_byte:child.end_byte].decode(
                            "utf-8", errors="replace",
                        )
                        break
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
        declarator = node.child_by_field_name("declarator")
        for _ in range(8):
            if declarator is None:
                return "<anonymous>"
            if declarator.type == Wrapper.FUNCTION_DECLARATOR:
                inner = declarator.child_by_field_name("declarator")
                if inner is None:
                    return "<anonymous>"
                if inner.type in (Identifier.IDENTIFIER, Identifier.FIELD_IDENTIFIER):
                    return content[inner.start_byte:inner.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                if inner.type == Identifier.QUALIFIED_IDENTIFIER:
                    for c in reversed(inner.children):
                        if c.type == Identifier.IDENTIFIER:
                            return content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            )
                    return "<anonymous>"
                if inner.type == Identifier.OPERATOR_NAME:
                    for c in inner.children:
                        if c.type != Identifier.OPERATOR:
                            return content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            ).strip()
                    return "<anonymous>"
                if inner.type == Identifier.DESTRUCTOR_NAME:
                    for c in inner.children:
                        if c.type == Identifier.IDENTIFIER:
                            return "~" + content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            )
                    return "<anonymous>"
                return "<anonymous>"
            if declarator.type in (
                Wrapper.POINTER_DECLARATOR, Wrapper.REFERENCE_DECLARATOR,
                Wrapper.PARENTHESIZED_DECLARATOR,
            ):
                declarator = declarator.child_by_field_name("declarator")
                continue
            break
        return "<anonymous>"
