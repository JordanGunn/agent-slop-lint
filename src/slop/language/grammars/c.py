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
    def try_nodes(cls) -> frozenset[str]:
        return frozenset()

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        return frozenset()

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
    def hidden_mutators(
        cls, fn_node: Any, content: bytes,
        *,
        require_type_annotation: bool = True,
    ) -> list[tuple[str, str, int]]:
        del require_type_annotation
        # Find function_declarator (unwrapping pointer-return declarators) +
        # extract non-const pointer params.
        declarator = fn_node.child_by_field_name("declarator")
        while declarator is not None and declarator.type == "pointer_declarator":
            declarator = declarator.child_by_field_name("declarator")
        if declarator is None or declarator.type != "function_declarator":
            return []
        plist = declarator.child_by_field_name("parameters")
        if plist is None:
            return []

        ptr_params: set[str] = set()
        for param in plist.children:
            name = _pointer_param_name(param, content)
            if name is not None:
                ptr_params.add(name)
        if not ptr_params:
            return []
        body = fn_node.child_by_field_name("body") or fn_node
        return _c_walk_pointer_mutations(body, content, ptr_params)

    @classmethod
    def stringly_typed_params(
        cls, fn_node: Any, content: bytes,
    ) -> list[tuple[str, bool]]:
        # Walk the declarator chain to find the function_declarator
        # holding the parameter_list.
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

        out: list[tuple[str, bool]] = []
        for param in plist.children:
            name = _char_pointer_param_name(param, content)
            if name is not None:
                out.append((name, True))
        return out

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


def _declarator_identifier(decl: Any, content: bytes) -> str | None:
    """Walk a pointer declarator chain to its inner identifier name, or None."""
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


def _pointer_param_name(param: Any, content: bytes) -> str | None:
    """Name of a non-const pointer parameter, or None."""
    if param.type != "parameter_declaration":
        return None
    has_const = False
    ptr_decl = None
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
    if has_const or ptr_decl is None:
        return None
    return _declarator_identifier(ptr_decl, content)


def _char_pointer_param_name(param: Any, content: bytes) -> str | None:
    """Name of a ``char*`` parameter, or None."""
    if param.type != "parameter_declaration":
        return None
    is_char = False
    ptr_decl = None
    for child in param.children:
        ctype = child.type
        if ctype == "primitive_type":
            ptext = content[child.start_byte:child.end_byte].decode(
                "utf-8", errors="replace",
            ).strip()
            if ptext == "char":
                is_char = True
        elif ctype == "pointer_declarator":
            ptr_decl = child
    if not is_char or ptr_decl is None:
        return None
    return _declarator_identifier(ptr_decl, content)


def _c_walk_pointer_mutations(
    body: Any, content: bytes, params: set[str],
) -> list[tuple[str, str, int]]:
    """Find assignments through pointer parameters in a C function body.

    Shapes:
      ``*p = ...``        — pointer_expression on LHS
      ``p->field = ...``  — field_expression on LHS with `->` operator
      ``p[i] = ...``      — subscript_expression on LHS
    """
    out: list[tuple[str, str, int]] = []
    stack = [body]
    while stack:
        n = stack.pop()
        if n.type == "assignment_expression":
            lhs = n.child_by_field_name("left")
            if lhs is not None:
                hit = _c_lhs_param(lhs, content, params)
                if hit is not None:
                    name, kind = hit
                    out.append((name, kind, n.start_point[0] + 1))
        stack.extend(n.children)
    return out


def _c_lhs_param(
    lhs: Any, content: bytes, params: set[str],
) -> tuple[str, str] | None:
    """Classify an assignment LHS as a pointer-param mutation, or None."""
    ltype = lhs.type
    if ltype == "pointer_expression":
        return _deref_assign_param(lhs, content, params)
    if ltype == "field_expression":
        return _field_assign_param(lhs, content, params)
    if ltype == "subscript_expression":
        return _subscript_assign_param(lhs, content, params)
    return None


def _identifier_child(node: Any) -> Any | None:
    """Return the first direct ``identifier`` child of a node, or None."""
    for c in node.children:
        if c.type == "identifier":
            return c
    return None


def _deref_assign_param(
    lhs: Any, content: bytes, params: set[str],
) -> tuple[str, str] | None:
    """``*p = ...`` — first identifier child that names a pointer param."""
    for child in lhs.children:
        if child.type == "identifier":
            name = content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            if name in params:
                return (name, "deref-assign")
    return None


def _field_assign_param(
    lhs: Any, content: bytes, params: set[str],
) -> tuple[str, str] | None:
    """``p->field = ...`` — arrow-operator field access on a pointer param."""
    if not any(c.type == "->" for c in lhs.children):
        return None
    obj = lhs.child_by_field_name("argument") or _identifier_child(lhs)
    if obj is not None and obj.type == "identifier":
        name = content[obj.start_byte:obj.end_byte].decode("utf-8", errors="replace")
        if name in params:
            return (name, "field-assign")
    return None


def _subscript_assign_param(
    lhs: Any, content: bytes, params: set[str],
) -> tuple[str, str] | None:
    """``p[i] = ...`` — subscript on a pointer param (argument field, else first id)."""
    argument = lhs.child_by_field_name("argument")
    if argument is not None and argument.type == "identifier":
        name = content[argument.start_byte:argument.end_byte].decode("utf-8", errors="replace")
        if name in params:
            return (name, "subscript-assign")
    ident = _identifier_child(lhs)
    if ident is not None:
        name = content[ident.start_byte:ident.end_byte].decode("utf-8", errors="replace")
        if name in params:
            return (name, "subscript-assign")
    return None
