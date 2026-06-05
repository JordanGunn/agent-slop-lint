"""Ruby grammar — classes + modules + methods; flat-body; positional names."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import MultiPurpose


class Ruby(MultiPurpose):
    id: ClassVar[str] = "ruby"

    @classmethod
    def member_access_patterns(cls) -> tuple[tuple[str, str], ...]:
        return (("call", "receiver"), ("element_reference", "object"))

    @classmethod
    def is_dynamic_language(cls) -> bool:
        return True

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"method", "singleton_method"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class", "module"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({"if", "elsif", "unless_modifier", "if_modifier",
                          "while_modifier", "until_modifier", "rescue_modifier",
                          "while", "until", "for", "when", "rescue", "conditional"})

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({"if", "unless_modifier", "while", "until", "for",
                          "case", "begin", "conditional", "do_block", "block"})

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"elsif", "when"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "binary"

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||", "and", "or"})

    @classmethod
    def if_nodes(cls) -> frozenset[str]:
        return frozenset({"if"})

    @classmethod
    def elif_nodes(cls) -> frozenset[str]:
        return frozenset({"elsif"})

    @classmethod
    def else_nodes(cls) -> frozenset[str]:
        return frozenset({"else"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({"while", "until", "for"})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({"case"})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({"when"})

    @classmethod
    def try_nodes(cls) -> frozenset[str]:
        return frozenset({"begin"})

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        return frozenset({"rescue"})

    @classmethod
    def body_field(cls) -> str:
        return ""  # flat-body

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({"body_statement"})

    @classmethod
    def body_skip_types(cls) -> frozenset[str]:
        return frozenset({
            "def", "end", "do", "then", "identifier", "operator",
            "method_parameters", "block_parameters", "lambda_parameters",
            "self", ".", "class", "module", "constant", "superclass",
            "if", "elsif", "else", "case", "when", "while", "until", "for", "in",
            "begin", "rescue", "ensure", "exceptions", "exception_variable",
        })

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"integer", "float", "complex", "rational"})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "def", "end", "class", "module", "if", "elsif", "else", "unless",
            "while", "until", "for", "in", "case", "when", "then", "do",
            "return", "yield", "break", "next", "redo", "retry",
            "begin", "rescue", "ensure", "raise", "require", "require_relative",
            "load", "include", "extend", "prepend", "public", "private", "protected",
            "attr_reader", "attr_writer", "attr_accessor", "lambda", "proc", "super",
            "self", "nil", "true", "false", "not", "and", "or",
            "=", "+", "-", "*", "/", "%", "**", "==", "===", "!=", "<", ">",
            "<=", ">=", "<=>", "&&", "||", "!", "&", "|", "^", "~", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=", "**=", "&&=", "||=", "..", "...",
            "=>", "->", "?", ":", ",", ".", "::",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "instance_variable", "class_variable", "global_variable",
            "constant", "integer", "float", "complex", "rational",
            "string", "string_content", "symbol", "simple_symbol", "hash_key_symbol",
            "true", "false", "nil",
        })

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return ((
            "((call method: (identifier) @method"
            " arguments: (argument_list (string (string_content) @module)))"
            " (#match? @method \"^(require|require_relative|load)$\"))",
            "ruby_require",
        ),)

    @classmethod
    def call_node_types(cls) -> frozenset[str]:
        return frozenset({"call"})

    @classmethod
    def extract_callee_name(cls, call_node: Any, content: bytes) -> str | None:
        method = call_node.child_by_field_name("method")
        if method is not None and method.type in ("identifier", "constant"):
            return content[method.start_byte:method.end_byte].decode("utf-8", errors="replace")
        return None

    @classmethod
    def language_builtins(cls) -> frozenset[str]:
        return frozenset({
            "puts", "print", "pp", "raise", "require", "require_relative", "load",
            "attr_reader", "attr_writer", "attr_accessor", "include", "extend",
            "prepend", "lambda", "proc", "new", "to_s", "to_i", "to_a", "to_h",
            "to_sym", "inspect", "send", "public_send", "freeze", "dup", "clone",
            "kind_of?", "is_a?", "respond_to?", "nil?", "empty?", "each", "map",
            "select", "reject", "reduce", "inject", "find", "any?", "all?", "none?",
            "first", "last", "size", "length", "count", "include?", "push", "pop",
            "shift", "unshift", "sort", "sort_by", "uniq", "flatten", "keys", "values", "fetch",
        })

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        del content
        if node.type == "module":
            return True
        if node.type == "class":
            return False
        return None

    @classmethod
    def string_annotated_parameters(cls, fn_node: Any, content: bytes) -> list[tuple[str, bool]]:
        params = fn_node.child_by_field_name("parameters")
        if params is None:
            return []
        out: list[tuple[str, bool]] = []
        for child in params.children:
            if child.type == "identifier":
                out.append((content[child.start_byte:child.end_byte].decode("utf-8", errors="replace"), False))
            elif child.type in ("optional_parameter", "keyword_parameter"):
                name_n = child.child_by_field_name("name") or next(
                    (c for c in child.children if c.type == "identifier"), None,
                )
                if name_n is not None:
                    out.append((content[name_n.start_byte:name_n.end_byte].decode("utf-8", errors="replace"), False))
        return out

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        if node.type == "module":
            return []
        for child in node.children:
            if child.type == "superclass":
                for sub in child.children:
                    if sub.type == "constant":
                        return [content[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace")]
        return []

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        if node.type not in ("method", "singleton_method"):
            return super().extract_name(node, content)
        saw_def = saw_self = saw_dot = False
        for child in node.children:
            ctype = child.type
            if ctype == "def":
                saw_def = True
                continue
            if not saw_def:
                continue
            if ctype == "self" and not saw_self:
                saw_self = True
                continue
            if ctype == "." and saw_self and not saw_dot:
                saw_dot = True
                continue
            if ctype in ("identifier", "operator"):
                return content[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
        return "<anonymous>"
