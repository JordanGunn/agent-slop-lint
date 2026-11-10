"""Python grammar — multi-paradigm (classes + free functions + lambdas)."""
from __future__ import annotations

from typing import Any, ClassVar

from ..paradigm import MultiPurpose
from ..paradigm.base import MemberAccess


class Python(MultiPurpose):
    id: ClassVar[str] = "python"

    @classmethod
    def is_dynamic_language(cls) -> bool:
        return True

    @classmethod
    def is_special_method(cls, name: str) -> bool:
        return name.startswith("__") and name.endswith("__")

    @classmethod
    def implicit_receiver_names(cls) -> frozenset[str]:
        return frozenset({"self", "cls"})

    @classmethod
    def member_access(cls) -> MemberAccess | None:
        return MemberAccess("attribute", "object", "attribute")

    @classmethod
    def instance_receiver(cls, method: Any, content: bytes) -> str | None:
        """The method's first parameter, unless it is decorated ``staticmethod`` or
        ``classmethod`` or is named ``cls`` (``__init_subclass__`` and metaclass methods
        take the class, not an instance)."""
        parent = method.parent
        if parent is not None and parent.type == "decorated_definition":
            for decorator in parent.children:
                if decorator.type != "decorator":
                    continue
                text = content[decorator.start_byte:decorator.end_byte].decode()
                if text.lstrip("@").split("(")[0].strip().split(".")[-1] in {"staticmethod", "classmethod"}:
                    return None
        parameters = method.child_by_field_name("parameters")
        first = parameters.named_children[0] if parameters is not None and parameters.named_children else None
        if first is None or first.type != "identifier":
            return None
        name = content[first.start_byte:first.end_byte].decode()
        return None if name == "cls" else name

    @classmethod
    def constructor_names(cls) -> frozenset[str]:
        return frozenset({"__init__", "__new__"})

    @classmethod
    def class_fields(cls, node: Any, content: bytes) -> tuple[str, ...]:
        """Names assigned or annotated directly in the class body (``x: int = 1``, ``y = 2``,
        ``z: str``); a tuple target (``a, b = ...``) names several and is not read."""
        body = node.child_by_field_name("body")
        names: list[str] = []
        for stmt in body.named_children if body is not None else ():
            if stmt.type != "expression_statement" or not stmt.named_children:
                continue
            assignment = stmt.named_children[0]
            target = assignment.child_by_field_name("left") if assignment.type == "assignment" else None
            if target is not None and target.type == "identifier":
                names.append(content[target.start_byte:target.end_byte].decode())
        return tuple(names)

    @classmethod
    def assignment_nodes(cls) -> frozenset[str]:
        # Augmented assignment (``self.v += 1``) is absent on purpose: it can only update an
        # attribute that already exists, so it declares nothing.
        return frozenset({"assignment"})

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
    def language_builtins(cls) -> frozenset[str]:
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
    def resolve_packages(cls, root, files):
        """A Python package is a directory containing ``__init__.py``."""
        from pathlib import Path as _Path
        by_dir = super().resolve_packages(root, files)
        return {
            name: dir_files
            for name, dir_files in by_dir.items()
            if any(_Path(f).name == "__init__.py" for f in dir_files)
        }

    @classmethod
    def package_init_name(cls) -> str | None:
        return "__init__.py"
