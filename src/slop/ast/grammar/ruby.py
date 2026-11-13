"""Ruby grammar — classes + modules + methods; flat-body; positional names."""
from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from .interface import Grammar, MemberAccess
from .imports import ModuleIndex, distinct
from .heritage import heritage


_MODULE = "module"
_ELSIF = "elsif"
_WHILE = "while"
_UNTIL = "until"


class Ruby(Grammar):
    id: ClassVar[str] = "ruby"

    @classmethod
    def class_scope_visible(cls) -> bool:
        return True

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        """Names as written, including the class and constant names (``constant``)."""
        return frozenset({"identifier", "constant"})

    @classmethod
    def member_access(cls) -> tuple[MemberAccess, ...]:
        """``self.m``; an instance variable (``@x``) is read from name binding."""
        return (MemberAccess("call", "receiver", "method"),)

    @classmethod
    def instance_receiver(cls, method: Any, content: bytes) -> str | None:
        """``self`` in an instance method; ``def self.m`` defines a method on the class itself."""
        del content
        return "self" if method.type == "method" else None

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"method", "singleton_method"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class", _MODULE})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({"if", _ELSIF, "unless_modifier", "if_modifier",
                          "while_modifier", "until_modifier", "rescue_modifier",
                          _WHILE, _UNTIL, "for", "when", "rescue", "conditional"})

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({"if", "unless_modifier", _WHILE, _UNTIL, "for",
                          "case", "begin", "conditional", "do_block", "block"})

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({_ELSIF, "when"})

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
        return frozenset({_ELSIF})

    @classmethod
    def else_nodes(cls) -> frozenset[str]:
        return frozenset({"else"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({_WHILE, _UNTIL, "for"})

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
            "self", ".", "class", _MODULE, "constant", "superclass",
            "if", _ELSIF, "else", "case", "when", _WHILE, _UNTIL, "for", "in",
            "begin", "rescue", "ensure", "exceptions", "exception_variable",
        })

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"integer", "float", "complex", "rational"})

    @classmethod
    def string_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"string"})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "def", "end", "class", _MODULE, "if", _ELSIF, "else", "unless",
            _WHILE, _UNTIL, "for", "in", "case", "when", "then", "do",
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
        return (
            ("((call method: (identifier) @method"
             " arguments: (argument_list (string (string_content) @module)))"
             " (#match? @method \"^(require|load)$\"))", "ruby_require"),
            ("((call method: (identifier) @method"
             " arguments: (argument_list (string (string_content) @module)))"
             " (#eq? @method \"require_relative\"))", "ruby_require_relative"),
        )

    @classmethod
    def resolve_import(cls, decl: Any, importer: Path, index: ModuleIndex) -> tuple[Any, ...]:
        """``require_relative`` names a file beside the requiring one, ``.rb`` optional."""
        if decl.kind != "ruby_require_relative":
            return super().resolve_import(decl, importer, index)
        return distinct([index.at(importer.parent / decl.specifier)])

    @classmethod
    def call_node_types(cls) -> frozenset[str]:
        return frozenset({"call"})

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
        if node.type == _MODULE:
            return True
        if node.type == "class":
            return False
        return None

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        if node.type == _MODULE:
            return []
        return heritage(node, content, ("superclass",))

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        if node.type not in ("method", "singleton_method"):
            return super().extract_name(node, content)
        saw_def = False
        for child in node.children:
            if child.type == "def":
                saw_def = True
            elif saw_def and child.type in ("identifier", "operator"):
                return content[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
        return "<anonymous>"
