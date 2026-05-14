"""Rust grammar — impl blocks + traits + free functions.

Inheritance-shaped queries (which Rust lacks) raise
``NotImplementedError`` if a rule reaches for them. The criterion for
``ObjectOriented`` membership is named scopes containing methods with
implicit receivers, not the full OOP suite.

Post-scan adjustment: Rust's methods live inside ``impl Type { fn m() {} }``
blocks rather than inside the struct/enum/trait body. The generic walker
parents inner ``function_item`` callables under the impl_item scope (or
sometimes under the file). ``post_scan_adjust`` rewrites them to be
parented under the impl's target type, so CK metrics find struct methods.
"""
from __future__ import annotations

import dataclasses
from typing import Any, ClassVar

from ..ast import Block, Callable, Conditional, Identifier, Literal, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class Rust(MultiPurpose):
    id: ClassVar[str] = "rust"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({Callable.FUNCTION_ITEM})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Scope.STRUCT_ITEM, Scope.TRAIT_ITEM, Scope.IMPL_ITEM})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({
            Identifier.IDENTIFIER, Identifier.FIELD_IDENTIFIER, Identifier.TYPE_IDENTIFIER,
        })

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_EXPRESSION,
            Loop.WHILE_EXPRESSION, Loop.FOR_EXPRESSION,
            Switch.MATCH_ARM,
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_EXPRESSION,
            Loop.WHILE_EXPRESSION, Loop.FOR_EXPRESSION,
            Switch.MATCH_EXPRESSION,                # container for match_arm
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({Switch.MATCH_ARM})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BINARY_EXPRESSION

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||"})

    @classmethod
    def if_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.IF_EXPRESSION})

    @classmethod
    def else_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.ELSE_CLAUSE})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({
            Loop.FOR_EXPRESSION, Loop.WHILE_EXPRESSION, Loop.LOOP_EXPRESSION,
        })

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.MATCH_EXPRESSION})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.MATCH_ARM})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({Block.BLOCK})

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        # Rust ``use foo::bar::Baz;`` — the use_declaration's argument is
        # a scoped_identifier (multi-segment), bare identifier (single
        # crate name), or scoped_use_list (``use foo::{a, b}`` — leading
        # crate captured via the scoped_identifier root).
        return (
            ("(use_declaration argument: (scoped_identifier) @module)", "use"),
            ("(use_declaration argument: (identifier) @module)", "use"),
            ("(use_declaration argument: (use_as_clause path: (scoped_identifier) @module))", "use"),
            ("(use_declaration argument: (use_as_clause path: (identifier) @module))", "use"),
            (
                "(use_declaration argument: (scoped_use_list path: (scoped_identifier) @module))",
                "use",
            ),
            (
                "(use_declaration argument: (scoped_use_list path: (identifier) @module))",
                "use",
            ),
        )

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.INTEGER_LITERAL, Literal.FLOAT_LITERAL})

    @classmethod
    def post_scan_adjust(cls, parse_result: Any) -> Any:
        """Rewrite Rust function_item callables inside impl blocks to parent under the target struct/enum/trait.

        Tree-sitter Python wraps the same underlying node in fresh
        Python objects per access (``id(n)`` isn't stable across
        traversals), so we identify impl_item nodes by their byte
        span ``(start_byte, end_byte)`` instead.
        """
        file_stem = parse_result.path.stem
        impl_target_by_span: dict[tuple[int, int], str] = {}

        def walk_impls(n: Any) -> None:
            if n.type == "impl_item":
                type_node = n.child_by_field_name("type")
                if type_node is not None:
                    target = _rust_target_type_name(type_node, parse_result.content)
                    if target is not None:
                        impl_target_by_span[(n.start_byte, n.end_byte)] = target
            for child in n.children:
                walk_impls(child)

        # Walk the AST from root. Pull root via any captured scope or
        # callable node's parent chain (.parent is stable here because
        # we're only using it to climb to the source_file root).
        root: Any = None
        for cn in list(parse_result.scope_nodes.values()) + list(parse_result.callable_nodes.values()):
            cur = cn
            while cur.parent is not None:
                cur = cur.parent
            root = cur
            break
        if root is None:
            return parse_result
        walk_impls(root)

        if not impl_target_by_span:
            return parse_result

        new_callables: list[Any] = []
        for c in parse_result.callables:
            node = parse_result.callable_nodes.get(c.qualname)
            if node is None:
                new_callables.append(c)
                continue
            target = _enclosing_impl_target(node, impl_target_by_span)
            if target is None:
                new_callables.append(c)
                continue
            new_parent = f"{file_stem}.{target}"
            simple = c.qualname.split(".")[-1]
            new_qualname = f"{new_parent}.{simple}"
            new_c = dataclasses.replace(
                c, parent=new_parent, qualname=new_qualname,
            )
            new_callables.append(new_c)
            if c.qualname in parse_result.callable_nodes:
                parse_result.callable_nodes[new_qualname] = parse_result.callable_nodes.pop(c.qualname)

        return dataclasses.replace(parse_result, callables=tuple(new_callables))


def _rust_target_type_name(type_node: Any, content: bytes) -> str | None:
    """Extract the type name from a Rust impl_item's ``type`` field."""
    if type_node.type == "type_identifier":
        return content[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
    if type_node.type == "generic_type":
        for child in type_node.children:
            if child.type == "type_identifier":
                return content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
    return None


def _enclosing_impl_target(
    node: Any, impl_target_by_span: dict[tuple[int, int], str],
) -> str | None:
    """Walk up from ``node`` looking for an enclosing impl_item span we have a target for."""
    cur = node.parent
    while cur is not None:
        if cur.type == "impl_item":
            target = impl_target_by_span.get((cur.start_byte, cur.end_byte))
            if target is not None:
                return target
        cur = cur.parent
    return None

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "fn", "if", "else", "for", "while", "loop", "match",
            "return", "break", "continue", "let", "mut", "ref",
            "struct", "enum", "impl", "trait", "type", "use", "mod",
            "pub", "self", "super", "crate", "as", "where",
            "async", "await", "unsafe", "move",
            "=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=",
            "=>", "::", "..", "..=", "?",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "field_identifier", "type_identifier",
            "integer_literal", "float_literal", "string_literal",
            "raw_string_literal", "char_literal", "boolean_literal",
            "true", "false",
        })
