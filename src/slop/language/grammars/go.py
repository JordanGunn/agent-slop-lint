"""Go grammar — struct + receiver-bound methods + free functions.

Tree-sitter-go syntactically distinguishes ``function_declaration``
(free) from ``method_declaration`` (receiver). Both are callables;
``functions()`` and ``methods()`` return distinct subsets.

Post-scan adjustment: Go's type_declaration node names its struct via
``type_spec.name`` (not via a direct ``name`` field on type_declaration),
so the default ``extract_name`` returns ``<anonymous>``. The
``extract_name`` override below walks the chain.

Additionally, Go method_declaration callables are emitted at the file
scope by the generic walker (their syntactic parent IS the file),
but semantically they belong to their receiver struct. ``post_scan_adjust``
rewrites each method_declaration callable's parent to point at the
receiver type's qualname.
"""
from __future__ import annotations

import dataclasses
from typing import Any, ClassVar

from ..ast import Block, Callable, Conditional, Identifier, Literal, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class Go(MultiPurpose):
    id: ClassVar[str] = "go"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Callable.FUNCTION_DECLARATION, Callable.METHOD_DECLARATION, Callable.FUNC_LITERAL,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        # Go doesn't have classes; struct + interface are the closest.
        return frozenset({Scope.TYPE_DECLARATION})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({
            Identifier.IDENTIFIER, Identifier.FIELD_IDENTIFIER, Identifier.TYPE_IDENTIFIER,
        })

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({Callable.FUNCTION_DECLARATION, Callable.FUNC_LITERAL})

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({Callable.METHOD_DECLARATION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT,
            Switch.EXPRESSION_CASE, Switch.TYPE_CASE, Switch.COMMUNICATION_CASE,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT,
            Switch.EXPRESSION_SWITCH_STATEMENT,
            Switch.TYPE_SWITCH_STATEMENT,
            Switch.SELECT_STATEMENT,
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({
            Switch.EXPRESSION_CASE, Switch.TYPE_CASE, Switch.COMMUNICATION_CASE,
        })

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
        return frozenset({Loop.FOR_STATEMENT})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.EXPRESSION_SWITCH_STATEMENT})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.EXPRESSION_CASE})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({Block.BLOCK})

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        # Go's import_spec covers both single-line ``import "foo"`` and
        # block ``import (...)`` forms — tree-sitter emits one
        # import_spec per imported package.
        return (
            ("(import_spec path: (interpreted_string_literal) @module)", "go_import"),
        )

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({
            Literal.INT_LITERAL, Literal.FLOAT_LITERAL,
            Literal.IMAGINARY_LITERAL, Literal.RUNE_LITERAL,
        })

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Walk Go's ``type_declaration → type_spec → name`` chain.

        Only returns a name when type_spec wraps a ``struct_type`` or
        ``interface_type`` — type aliases (``type T int``) are NOT
        classes; CK metrics should skip them. Returns ``<anonymous>``
        for non-struct/non-interface type declarations so they fall
        through CK iteration (anonymous classes contribute 0 to NOC
        since superclasses_of returns []).
        """
        if node.type != "type_declaration":
            return super().extract_name(node, content)
        for spec in node.children:
            if spec.type != "type_spec":
                continue
            name_node = spec.child_by_field_name("name")
            type_node = spec.child_by_field_name("type")
            if name_node is None or type_node is None:
                continue
            if type_node.type in ("struct_type", "interface_type"):
                return content[name_node.start_byte:name_node.end_byte].decode(
                    "utf-8", errors="replace",
                )
        return "<anonymous>"

    @classmethod
    def post_scan_adjust(cls, parse_result: Any) -> Any:
        """Rewrite Go method_declaration callables to parent under their receiver struct.

        The generic walker assigns each method_declaration's parent
        based on syntactic nesting (file scope, since methods appear
        at top-level in Go). For CK metrics to find methods of a
        struct, we re-parent them to ``<file_stem>.<ReceiverType>``.
        """
        # Find struct/interface scope qualnames by simple name in this file.
        # Generic walker has already emitted them via type_declaration class scopes.
        file_stem = parse_result.path.stem
        new_callables: list[Any] = []
        # Build a quick lookup: receiver type → AST node for each method_declaration.
        receiver_by_line: dict[int, str] = {}

        def walk(n: Any) -> None:
            if n.type == "method_declaration":
                receiver = _go_receiver_type_name(n, parse_result.content)
                if receiver is not None:
                    receiver_by_line[n.start_point[0] + 1] = receiver
            for child in n.children:
                walk(child)

        # Walk the saved callable nodes to find their parent contexts. The
        # callable_nodes dict gives us each method_declaration's AST node
        # directly, so we can read the receiver field without re-parsing.
        for c in parse_result.callables:
            node = parse_result.callable_nodes.get(c.qualname)
            if node is None or node.type != "method_declaration":
                new_callables.append(c)
                continue
            receiver = _go_receiver_type_name(node, parse_result.content)
            if receiver is None:
                new_callables.append(c)
                continue
            new_parent = f"{file_stem}.{receiver}"
            # Rebuild Callable with adjusted parent. Also rebuild qualname
            # to reflect the new parent path so methods_of(scope) finds them.
            simple = c.qualname.split(".")[-1]
            new_qualname = f"{new_parent}.{simple}"
            new_c = dataclasses.replace(c, parent=new_parent, qualname=new_qualname)
            new_callables.append(new_c)
            # Rewire callable_nodes for the new qualname.
            if c.qualname in parse_result.callable_nodes:
                parse_result.callable_nodes[new_qualname] = parse_result.callable_nodes.pop(c.qualname)

        return dataclasses.replace(parse_result, callables=tuple(new_callables))


def _go_receiver_type_name(method_node: Any, content: bytes) -> str | None:
    """Extract the receiver type name from a Go ``method_declaration``.

    Strips pointer indirection (``func (s *S) M()`` → ``S``). Returns
    None if the receiver doesn't expose a recognisable type identifier.
    """
    receiver = method_node.child_by_field_name("receiver")
    if receiver is None:
        return None
    for child in receiver.children:
        if child.type == "parameter_declaration":
            type_node = child.child_by_field_name("type")
            if type_node is None:
                continue
            if type_node.type == "pointer_type":
                for pc in type_node.children:
                    if pc.type == "type_identifier":
                        return content[pc.start_byte:pc.end_byte].decode("utf-8", errors="replace")
            elif type_node.type == "type_identifier":
                return content[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    return None

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "func", "if", "else", "for", "switch", "case", "default",
            "return", "break", "continue", "go", "defer", "select",
            "range", "type", "struct", "interface", "map", "chan",
            "import", "package", "var", "const",
            "=", ":=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=",
            "++", "--", "<-", "...",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "field_identifier", "type_identifier",
            "package_identifier",
            "int_literal", "float_literal", "imaginary_literal",
            "rune_literal", "raw_string_literal", "interpreted_string_literal",
            "true", "false", "nil", "iota",
        })
