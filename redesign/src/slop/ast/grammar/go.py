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


class Go(MultiPurpose):
    id: ClassVar[str] = "go"

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
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(parameter_declaration type: (_) @annotation)", "param"),
            ("(function_declaration result: (_) @annotation)", "return"),
            ("(method_declaration result: (_) @annotation)", "return"),
        )

    @classmethod
    def is_dynamic_type(cls, text: str) -> bool:
        cleaned = text.strip()
        return cleaned in ("any", "interface{}") or cleaned.startswith("interface{}")

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
            if spec.type != "type_spec":
                continue
            name_node = spec.child_by_field_name("name")
            type_node = spec.child_by_field_name("type")
            if name_node is None or type_node is None:
                continue
            if type_node.type in ("struct_type", "interface_type"):
                return content[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
        return "<anonymous>"

    @classmethod
    def reparent_callable(cls, node: Any, content: bytes) -> str | None:
        if node.type != "method_declaration":
            return None
        return _go_receiver_type_name(node, content)

    @classmethod
    def parameter_mutations(cls, fn_node: Any, content: bytes) -> list[tuple[str, str, int]]:
        params = _go_parameter_names(fn_node, content)
        if not params:
            return []
        body = fn_node.child_by_field_name("body") or fn_node
        out: list[tuple[str, str, int]] = []
        stack = [body]
        while stack:
            n = stack.pop()
            if n.type == "assignment_statement":
                rhs = n.child_by_field_name("right")
                if rhs is not None:
                    for call in _go_iter_calls(rhs):
                        target = _go_append_target(call, content, params)
                        if target is not None:
                            out.append((target, "append", n.start_point[0] + 1))
            stack.extend(n.children)
        return out


def _go_receiver_type_name(method_node: Any, content: bytes) -> str | None:
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


def _go_parameter_names(fn_node: Any, content: bytes) -> set[str]:
    plist = fn_node.child_by_field_name("parameters")
    if plist is None:
        return set()
    names: set[str] = set()
    for decl in plist.children:
        if decl.type != "parameter_declaration":
            continue
        for child in decl.children:
            if child.type == "identifier":
                names.add(content[child.start_byte:child.end_byte].decode("utf-8", errors="replace"))
    return names


def _go_iter_calls(node: Any):
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type == "call_expression":
            yield n
        stack.extend(n.children)


def _go_append_target(call_node: Any, content: bytes, params: set[str]) -> str | None:
    fn_child = call_node.child_by_field_name("function")
    if fn_child is None or fn_child.type != "identifier":
        return None
    if content[fn_child.start_byte:fn_child.end_byte].decode("utf-8", errors="replace") != "append":
        return None
    args = call_node.child_by_field_name("arguments")
    if args is None:
        return None
    for arg in args.children:
        if arg.type == "identifier":
            name = content[arg.start_byte:arg.end_byte].decode("utf-8", errors="replace")
            return name if name in params else None
        if arg.type not in ("(", ")", ","):
            return None
    return None
