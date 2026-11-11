"""Go grammar — structs + receiver methods + free functions (MultiPurpose).

Receiver methods are emitted at file top-level by tree-sitter but belong to their
receiver type; ``reparent_callable`` returns the receiver name so the carver
attaches them to the struct by construction (the legacy used a post_scan_adjust
record-rewrite — dropped). Also fixes a legacy bug where operator_nodes/
operand_nodes were nested inside a helper and never took effect.
"""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import MultiPurpose
from ..paradigm.base import MemberAccess


class Go(MultiPurpose):
    id: ClassVar[str] = "go"

    @classmethod
    def member_access(cls) -> MemberAccess | None:
        """``r.x`` and the callee of ``r.m()``: Go always writes the receiver."""
        return MemberAccess("selector_expression", "operand", "field")

    @classmethod
    def instance_receiver(cls, method: Any, content: bytes) -> str | None:
        """The receiver's name in ``func (s *Stack) Push()``; an unnamed receiver
        (``func (Stack) Len()``) or a plain function has no instance it can reach."""
        receivers = method.child_by_field_name("receiver")
        declared = receivers.named_children if receivers is not None else []
        name = declared[0].child_by_field_name("name") if declared else None
        return content[name.start_byte:name.end_byte].decode("utf-8") if name is not None else None

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_declaration", "method_declaration", "func_literal"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"type_declaration"})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({"identifier", "field_identifier", "type_identifier"})

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({"function_declaration", "func_literal"})

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({"method_declaration"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement",
                          "expression_case", "type_case", "communication_case"})

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "expression_switch_statement",
                          "type_switch_statement", "select_statement"})

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"expression_case", "type_case", "communication_case"})

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
        return frozenset({"for_statement"})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({"expression_switch_statement"})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({"expression_case"})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({"block"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"int_literal", "float_literal", "imaginary_literal", "rune_literal"})

    @classmethod
    def string_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"interpreted_string_literal", "raw_string_literal"})

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
            "+=", "-=", "*=", "/=", "%=", "++", "--", "<-", "...",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "field_identifier", "type_identifier", "package_identifier",
            "int_literal", "float_literal", "imaginary_literal",
            "rune_literal", "raw_string_literal", "interpreted_string_literal",
            "true", "false", "nil", "iota",
        })

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (("(import_spec path: (interpreted_string_literal) @module)", "go_import"),)

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        del content
        if node.type != "type_declaration":
            return None
        for child in node.children:
            if child.type != "type_spec":
                continue
            inner = child.child_by_field_name("type")
            if inner is None:
                continue
            if inner.type == "interface_type":
                return True
            if inner.type == "struct_type":
                return False
        return None

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        if node.type != "type_declaration":
            return super().extract_name(node, content)
        for spec in node.children:
            if spec.type not in ("type_spec", "type_alias"):
                continue
            name_node = spec.child_by_field_name("name")
            if name_node is not None:
                return content[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
        return "<anonymous>"

    @classmethod
    def reparent_callable(cls, node: Any, content: bytes) -> str | None:
        if node.type != "method_declaration":
            return None
        return _go_receiver_type_name(node, content)


def _go_receiver_type_name(method_node: Any, content: bytes) -> str | None:
    receiver = method_node.child_by_field_name("receiver")
    if receiver is None:
        return None
    for child in receiver.children:
        if child.type != "parameter_declaration":
            continue
        name = _go_type_identifier(child.child_by_field_name("type"))
        if name is not None:
            return content[name.start_byte:name.end_byte].decode("utf-8", errors="replace")
    return None


def _go_type_identifier(type_node: Any) -> Any | None:
    if type_node is None:
        return None
    if type_node.type == "pointer_type":
        for child in type_node.children:
            if child.type == "type_identifier":
                return child
    elif type_node.type == "type_identifier":
        return type_node
    return None
