"""Python grammar — multi-paradigm (classes + free functions + lambdas)."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigms import MultiPurpose


class Python(MultiPurpose):
    id: ClassVar[str] = "python"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_definition", "async_function_definition", "lambda"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_definition"})

    @classmethod
    def methods(cls) -> frozenset[str]:
        # Lambdas can't be Python methods.
        return frozenset({"function_definition", "async_function_definition"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_statement", "elif_clause",
            "for_statement", "while_statement",
            "except_clause",
            "conditional_expression",   # x if c else y
            "case_clause",              # match/case
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            "if_statement", "for_statement", "while_statement",
            "except_clause", "conditional_expression",
            "match_statement",          # container for case_clause
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({"elif_clause", "case_clause"})

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return "boolean_operator"   # dedicated node; counts and/or

    @classmethod
    def elif_nodes(cls) -> frozenset[str]:
        return frozenset({"elif_clause"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({"for_statement", "while_statement"})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({"match_statement"})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({"case_clause"})

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        return frozenset({"except_clause"})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({"block"})

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"integer", "float"})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            "def", "if", "else", "elif", "for", "while", "return",
            "class", "import", "from", "try", "except", "finally",
            "raise", "with", "as", "yield", "lambda", "del", "assert",
            "break", "continue", "pass", "and", "or", "not", "in", "is",
            "=", "+", "-", "*", "/", "**", "//", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "|", "&", "^", "~", "<<", ">>",
            "+=", "-=", "*=", "/=", "//=", "%=", "**=",
            "->", "@",
        })

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        return frozenset({
            "identifier", "integer", "float", "string",
            "true", "false", "none", "type",
        })

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(import_statement name: (dotted_name) @module)", "import"),
            ("(import_from_statement module_name: (dotted_name) @module)", "from_import"),
            ("(import_statement name: (aliased_import name: (dotted_name) @module))", "import"),
            ("(import_from_statement module_name: (relative_import) @module)", "from_import"),
        )

    @classmethod
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(typed_parameter type: (_) @annotation)", "param"),
            ("(typed_default_parameter type: (_) @annotation)", "param"),
            ("(function_definition return_type: (_) @annotation)", "return"),
            ("(assignment type: (_) @annotation)", "variable"),
        )

    @classmethod
    def is_escape_hatch_text(cls, text: str) -> bool:
        return text.strip() == "Any" or "Any" in _python_type_tokens(text)

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        sc_node = node.child_by_field_name("superclasses")
        if sc_node is None:
            return []
        out: list[str] = []
        for child in sc_node.children:
            if child.type == "identifier":
                out.append(content[child.start_byte:child.end_byte].decode("utf-8", errors="replace"))
            elif child.type == "attribute":
                text = content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                out.append(text.split(".")[-1])
        return out

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        if node.type != "class_definition":
            return None
        for b in cls.extract_superclasses(node, content):
            if b in ("ABC", "Protocol", "ABCMeta"):
                return True
        return False

    @classmethod
    def call_node_types(cls) -> frozenset[str]:
        return frozenset({"call"})

    @classmethod
    def extract_callee_name(cls, call_node: Any, content: bytes) -> str | None:
        fn_child = call_node.child_by_field_name("function")
        if fn_child is None:
            return None
        if fn_child.type == "identifier":
            return content[fn_child.start_byte:fn_child.end_byte].decode("utf-8", errors="replace")
        if fn_child.type == "attribute":
            attr = fn_child.child_by_field_name("attribute")
            if attr is not None:
                return content[attr.start_byte:attr.end_byte].decode("utf-8", errors="replace")
        return None

    @classmethod
    def trivial_callees(cls) -> frozenset[str]:
        return frozenset({
            "print", "len", "range", "sorted", "reversed", "enumerate", "zip",
            "map", "filter", "any", "all", "sum", "min", "max", "abs", "round",
            "list", "dict", "set", "tuple", "str", "int", "float", "bool",
            "isinstance", "issubclass", "type", "id", "hash", "repr", "getattr",
            "setattr", "hasattr", "delattr", "callable", "iter", "next",
            "open", "input", "super", "vars", "dir", "locals", "globals",
            "staticmethod", "classmethod", "property",
            "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
            "AttributeError", "RuntimeError", "StopIteration", "NotImplementedError",
            "True", "False", "None",
        })

    @classmethod
    def hidden_mutators(
        cls, fn_node: Any, content: bytes, *, require_type_annotation: bool = True,
    ) -> list[tuple[str, str, int]]:
        params_node = fn_node.child_by_field_name("parameters")
        if params_node is None:
            return []
        candidates: set[str] = set()
        for child in params_node.children:
            ptype = child.type
            if ptype == "identifier":
                if not require_type_annotation:
                    candidates.add(_text(child, content))
            elif ptype in ("typed_parameter", "typed_default_parameter"):
                name_n = child.child_by_field_name("name") or next(
                    (c for c in child.children if c.type == "identifier"), None,
                )
                if name_n is None:
                    continue
                pname = _text(name_n, content)
                type_n = child.child_by_field_name("type")
                if not require_type_annotation:
                    candidates.add(pname)
                elif type_n is not None and (
                    _python_type_tokens(_text(type_n, content)) & _PYTHON_COLLECTION_TYPES
                ):
                    candidates.add(pname)
            elif ptype == "default_parameter" and not require_type_annotation:
                name_n = child.child_by_field_name("name")
                if name_n is not None:
                    candidates.add(_text(name_n, content))
        if not candidates:
            return []
        body = fn_node.child_by_field_name("body") or fn_node
        out: list[tuple[str, str, int]] = []
        stack = [body]
        while stack:
            n = stack.pop()
            if n.type == "call":
                fn_child = n.child_by_field_name("function")
                if fn_child is not None and fn_child.type == "attribute":
                    obj_n = fn_child.child_by_field_name("object")
                    attr_n = fn_child.child_by_field_name("attribute")
                    if obj_n is not None and attr_n is not None and obj_n.type == "identifier":
                        obj_name = _text(obj_n, content)
                        method = _text(attr_n, content)
                        if obj_name in candidates and method in _PYTHON_MUTATIONS:
                            out.append((obj_name, method, n.start_point[0] + 1))
            stack.extend(n.children)
        return out

    @classmethod
    def stringly_typed_params(cls, fn_node: Any, content: bytes) -> list[tuple[str, bool]]:
        params_node = fn_node.child_by_field_name("parameters")
        if params_node is None:
            return []
        out: list[tuple[str, bool]] = []
        for child in params_node.children:
            ptype = child.type
            if ptype == "identifier":
                out.append((_text(child, content), False))
            elif ptype in ("typed_parameter", "typed_default_parameter"):
                name_n = child.child_by_field_name("name") or next(
                    (c for c in child.children if c.type == "identifier"), None,
                )
                if name_n is None:
                    continue
                type_n = child.child_by_field_name("type")
                has_str = type_n is not None and "str" in _python_type_tokens(_text(type_n, content))
                out.append((_text(name_n, content), has_str))
        return out

    @classmethod
    def resolve_packages(cls, root, files):
        """A Python package is a directory containing ``__init__.py``."""
        from pathlib import Path as _Path
        by_dir = super().resolve_packages(root, files)
        return {
            name: dir_files
            for name, dir_files in by_dir.items()
            if any(_Path(f).name == "__init__.py" for f in dir_files)
        }


_PYTHON_COLLECTION_TYPES: frozenset[str] = frozenset({
    "list", "List", "dict", "Dict", "set", "Set",
    "MutableSequence", "MutableMapping", "MutableSet", "Sequence", "Mapping",
    "deque", "Deque", "defaultdict", "Counter",
})

_PYTHON_MUTATIONS: frozenset[str] = frozenset({
    "append", "extend", "insert", "remove", "pop", "clear", "sort", "reverse",
    "update", "setdefault", "popitem", "add", "discard",
    "intersection_update", "difference_update", "symmetric_difference_update",
})


def _text(node: Any, content: bytes) -> str:
    return content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _python_type_tokens(text: str) -> set[str]:
    """Split a type annotation into identifier-like tokens."""
    out: set[str] = set()
    buf: list[str] = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            buf.append(ch)
        elif buf:
            out.add("".join(buf)); buf = []
    if buf:
        out.add("".join(buf))
    return out
