"""JavaScript grammar — classes + free functions + arrow functions."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import MultiPurpose


class JavaScript(MultiPurpose):
    id: ClassVar[str] = "javascript"

    @classmethod
    def member_access_patterns(cls) -> tuple[tuple[str, str], ...]:
        return (("member_expression", "object"), ("subscript_expression", "object"))

    @classmethod
    def is_dynamic_language(cls) -> bool:
        return True

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_declaration", "function_expression", "arrow_function",
                          "method_definition", "generator_function_declaration"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_declaration"})

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        return frozenset({"identifier", "property_identifier"})

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({"function_declaration", "function_expression",
                          "arrow_function", "generator_function_declaration"})

    @classmethod
    def methods(cls) -> frozenset[str]:
        return frozenset({"method_definition"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "for_in_statement", "for_of_statement",
                          "while_statement", "do_statement", "switch_case", "catch_clause",
                          "ternary_expression"})

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "for_in_statement", "for_of_statement",
                          "while_statement", "do_statement", "switch_statement", "catch_clause",
                          "ternary_expression"})

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"switch_case"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary_expression"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||", "??"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({"for_statement", "for_in_statement", "for_of_statement",
                          "while_statement", "do_statement"})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({"switch_statement"})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({"switch_case"})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({"statement_block"})

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        return frozenset({"switch_body"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"number"})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "function", "if", "else", "for", "while", "do", "return", "class",
            "import", "from", "try", "catch", "finally", "throw", "new", "delete",
            "typeof", "instanceof", "void", "switch", "case", "default", "break",
            "continue", "var", "let", "const", "yield", "await", "async",
            "=", "+", "-", "*", "/", "%", "**", "==", "!=", "===", "!==",
            "<", ">", "<=", ">=", "&&", "||", "??", "!", "~", "&", "|", "^",
            "<<", ">>", ">>>", "+=", "-=", "*=", "/=", "%=", "**=",
            "++", "--", "=>", "...", "?",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "property_identifier", "shorthand_property_identifier",
            "number", "string", "string_fragment", "template_string", "regex",
            "true", "false", "null", "undefined",
        })

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(import_statement source: (string (string_fragment) @module))", "esm"),
            ("((call_expression function: (identifier) @fn"
             " arguments: (arguments (string (string_fragment) @module)))"
             " (#eq? @fn \"require\"))", "require"),
        )

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        del content
        return False if node.type == "class_declaration" else None

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        out: list[str] = []
        for child in node.children:
            if child.type == "class_heritage":
                for c in child.children:
                    if c.type == "identifier":
                        out.append(content[c.start_byte:c.end_byte].decode("utf-8", errors="replace"))
        return out

    @classmethod
    def parameter_mutations(cls, fn_node: Any, content: bytes) -> list[tuple[str, str, int]]:
        # JS has no static types to gate parameter-mutation detection on.
        del fn_node, content
        return []


_JS_MUTATION_METHODS: frozenset[str] = frozenset({
    "push", "pop", "splice", "shift", "unshift", "sort", "reverse", "fill",
    "set", "delete", "clear", "add",
})
_TS_MUTABLE_TYPES: frozenset[str] = frozenset({
    "Array", "Map", "Set", "WeakMap", "WeakSet", "ReadonlyArray",
})


def _decode(node: Any, content: bytes) -> str:
    return content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _type_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    buf: list[str] = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            buf.append(ch)
        elif buf:
            tokens.add("".join(buf)); buf = []
    if buf:
        tokens.add("".join(buf))
    return tokens


def _ts_collection_param(child: Any, content: bytes) -> str | None:
    if child.type not in ("required_parameter", "optional_parameter"):
        return None
    pattern = child.child_by_field_name("pattern")
    if pattern is None or pattern.type != "identifier":
        return None
    name = _decode(pattern, content)
    type_ann = child.child_by_field_name("type")
    if type_ann is None:
        return None
    return name if _type_tokens(_decode(type_ann, content)) & _TS_MUTABLE_TYPES else None


def _ts_collection_param_names(fn_node: Any, content: bytes) -> set[str]:
    params_node = fn_node.child_by_field_name("parameters")
    if params_node is None:
        return set()
    names: set[str] = set()
    for child in params_node.children:
        name = _ts_collection_param(child, content)
        if name is not None:
            names.add(name)
    return names


def _js_mutation_call(n: Any, content: bytes, params: set[str]) -> tuple[str, str] | None:
    fn_child = n.child_by_field_name("function")
    if fn_child is None or fn_child.type != "member_expression":
        return None
    obj = fn_child.child_by_field_name("object")
    prop = fn_child.child_by_field_name("property")
    if obj is None or prop is None or obj.type != "identifier" or prop.type not in ("property_identifier", "identifier"):
        return None
    obj_name = _decode(obj, content)
    method = _decode(prop, content)
    return (obj_name, method) if obj_name in params and method in _JS_MUTATION_METHODS else None


def _js_walk_mutations(body: Any, content: bytes, params: set[str]) -> list[tuple[str, str, int]]:
    out: list[tuple[str, str, int]] = []
    stack = [body]
    while stack:
        n = stack.pop()
        if n.type == "call_expression":
            hit = _js_mutation_call(n, content, params)
            if hit is not None:
                out.append((hit[0], hit[1], n.start_point[0] + 1))
        stack.extend(n.children)
    return out
