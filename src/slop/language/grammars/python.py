"""Python grammar — class-and-function-emitting, multi-paradigm."""
from __future__ import annotations

from typing import Any, ClassVar

from ..ast import Block, Callable, Catch, Conditional, Literal, Loop, Operator, Scope, Switch
from ..multipurpose import MultiPurpose


class Python(MultiPurpose):
    id: ClassVar[str] = "python"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({
            Callable.FUNCTION_DEFINITION,
            Callable.ASYNC_FUNCTION_DEFINITION,
            Callable.LAMBDA,
        })

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({Scope.CLASS_DEFINITION})

    @classmethod
    def methods(cls) -> frozenset[str]:
        # Lambdas can't be methods in Python (no `def` inside class via lambda).
        return frozenset({Callable.FUNCTION_DEFINITION, Callable.ASYNC_FUNCTION_DEFINITION})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT, Conditional.ELIF_CLAUSE,
            Loop.FOR_STATEMENT, Loop.WHILE_STATEMENT,
            Catch.EXCEPT_CLAUSE,
            Conditional.CONDITIONAL_EXPRESSION,    # x if cond else y
            Switch.CASE_CLAUSE,                    # match/case (PEP 634)
        })

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({
            Conditional.IF_STATEMENT,
            Loop.FOR_STATEMENT, Loop.WHILE_STATEMENT,
            Catch.EXCEPT_CLAUSE,
            Conditional.CONDITIONAL_EXPRESSION,
            Switch.MATCH_STATEMENT,                # container for case_clause
        })

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        return frozenset({
            Conditional.ELIF_CLAUSE,               # syntactically inside if_statement
            Switch.CASE_CLAUSE,                    # syntactically inside match_statement
        })

    @classmethod
    def boolean_op_node(cls) -> str | None:
        return Operator.BOOLEAN_OPERATOR

    # boolean_op_operators defaults to None — Python's dedicated
    # boolean_operator node always counts (and/or).

    @classmethod
    def if_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.IF_STATEMENT})

    @classmethod
    def elif_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.ELIF_CLAUSE})

    @classmethod
    def else_nodes(cls) -> frozenset[str]:
        return frozenset({Conditional.ELSE_CLAUSE})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({Loop.FOR_STATEMENT, Loop.WHILE_STATEMENT})

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.MATCH_STATEMENT})

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset({Switch.CASE_CLAUSE})

    @classmethod
    def try_nodes(cls) -> frozenset[str]:
        return frozenset({Catch.TRY_STATEMENT})

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        return frozenset({Catch.EXCEPT_CLAUSE})

    @classmethod
    def block_types(cls) -> frozenset[str]:
        return frozenset({Block.BLOCK})

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(import_statement name: (dotted_name) @module)", "import"),
            ("(import_from_statement module_name: (dotted_name) @module)", "from_import"),
            # ``import foo as bar`` wraps the dotted_name in aliased_import.
            ("(import_statement name: (aliased_import name: (dotted_name) @module))", "import"),
            ("(import_from_statement module_name: (relative_import) @module)", "from_import"),
        )

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        return frozenset({Literal.INTEGER, Literal.FLOAT})

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        return frozenset({
            # Keywords
            "def", "if", "else", "elif", "for", "while", "return",
            "class", "import", "from", "try", "except", "finally",
            "raise", "with", "as", "yield", "lambda", "del", "assert",
            "break", "continue", "pass", "and", "or", "not", "in", "is",
            # Operator symbols
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
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """Python: ``class Foo(Bar, Mixin):`` — superclasses field."""
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
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(typed_parameter type: (_) @annotation)", "param"),
            ("(typed_default_parameter type: (_) @annotation)", "param"),
            ("(function_definition return_type: (_) @annotation)", "return"),
            # ``x: T = ...`` and bare ``x: T`` annotated assignments.
            # tree-sitter-python emits these as ``assignment`` with a
            # ``type`` field present.
            ("(assignment type: (_) @annotation)", "variable"),
        )

    @classmethod
    def is_escape_hatch_text(cls, text: str) -> bool:
        # Match ``Any`` as a bare token. Strip generic / union baggage:
        # ``Optional[Any]`` and ``list[Any]`` both count as Any-bearing.
        return text.strip() == "Any" or "Any" in _python_type_tokens(text)

    @classmethod
    def hidden_mutators(
        cls, fn_node: Any, content: bytes,
        *,
        require_type_annotation: bool = True,
    ) -> list[tuple[str, str, int]]:
        params_node = fn_node.child_by_field_name("parameters")
        if params_node is None:
            return []
        candidates: set[str] = set()
        for child in params_node.children:
            ptype = child.type
            if ptype == "identifier":
                if not require_type_annotation:
                    name = content[child.start_byte:child.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                    candidates.add(name)
            elif ptype in ("typed_parameter", "typed_default_parameter"):
                name_n = child.child_by_field_name("name") or next(
                    (c for c in child.children if c.type == "identifier"), None,
                )
                type_n = child.child_by_field_name("type")
                if name_n is None:
                    continue
                pname = content[name_n.start_byte:name_n.end_byte].decode(
                    "utf-8", errors="replace",
                )
                if not require_type_annotation:
                    candidates.add(pname)
                elif type_n is not None:
                    type_text = content[type_n.start_byte:type_n.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                    tokens = _python_type_tokens(type_text)
                    if tokens & _PYTHON_COLLECTION_TYPES:
                        candidates.add(pname)
            elif ptype == "default_parameter" and not require_type_annotation:
                name_n = child.child_by_field_name("name")
                if name_n is not None:
                    candidates.add(content[name_n.start_byte:name_n.end_byte].decode(
                        "utf-8", errors="replace",
                    ))
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
                    if (
                        obj_n is not None
                        and attr_n is not None
                        and obj_n.type == "identifier"
                    ):
                        obj_name = content[obj_n.start_byte:obj_n.end_byte].decode(
                            "utf-8", errors="replace",
                        )
                        method = content[attr_n.start_byte:attr_n.end_byte].decode(
                            "utf-8", errors="replace",
                        )
                        if obj_name in candidates and method in _PYTHON_MUTATIONS:
                            out.append((obj_name, method, n.start_point[0] + 1))
            stack.extend(n.children)
        return out

    @classmethod
    def stringly_typed_params(
        cls, fn_node: Any, content: bytes,
    ) -> list[tuple[str, bool]]:
        params_node = fn_node.child_by_field_name("parameters")
        if params_node is None:
            return []
        out: list[tuple[str, bool]] = []
        for child in params_node.children:
            ptype = child.type
            if ptype == "identifier":
                name = content[child.start_byte:child.end_byte].decode(
                    "utf-8", errors="replace",
                )
                out.append((name, False))
            elif ptype in ("typed_parameter", "typed_default_parameter"):
                name_n = child.child_by_field_name("name") or next(
                    (c for c in child.children if c.type == "identifier"), None,
                )
                type_n = child.child_by_field_name("type")
                if name_n is None:
                    continue
                name = content[name_n.start_byte:name_n.end_byte].decode(
                    "utf-8", errors="replace",
                )
                has_str = False
                if type_n is not None:
                    type_text = content[
                        type_n.start_byte:type_n.end_byte
                    ].decode("utf-8", errors="replace")
                    # Token-aware match: "str", "Optional[str]", "str | None".
                    has_str = "str" in _python_type_tokens(type_text)
                out.append((name, has_str))
        return out

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
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        """A class inheriting from ABC / Protocol / ABCMeta is abstract.

        Anything else is concrete. Python doesn't have an ``abstract``
        keyword; abstraction is signalled by base class.
        """
        if node.type != Scope.CLASS_DEFINITION:
            return None
        bases = cls.extract_superclasses(node, content)
        for b in bases:
            if b in ("ABC", "Protocol", "ABCMeta"):
                return True
        return False

    @classmethod
    def resolve_packages(cls, root: Any, files: list[Any]) -> dict[str, list[Any]]:
        """A Python package is a directory containing ``__init__.py``.

        Directories without ``__init__.py`` are dropped — their files
        are module-level scripts, not part of a package. This matches
        importlib's package-discovery semantics and the legacy kernel.
        """
        from pathlib import Path as _Path

        by_dir = super().resolve_packages(root, files)
        result: dict[str, list[_Path]] = {}
        for name, dir_files in by_dir.items():
            if any(_Path(f).name == "__init__.py" for f in dir_files):
                result[name] = list(dir_files)
        return result  # type: ignore[return-value]


_PYTHON_COLLECTION_TYPES: frozenset[str] = frozenset({
    "list", "List", "dict", "Dict", "set", "Set",
    "MutableSequence", "MutableMapping", "MutableSet",
    "Sequence", "Mapping",
    "deque", "Deque", "defaultdict", "Counter",
})

_PYTHON_MUTATIONS: frozenset[str] = frozenset({
    # list
    "append", "extend", "insert", "remove", "pop", "clear",
    "sort", "reverse",
    # dict
    "update", "setdefault", "popitem",
    # set
    "add", "discard",
    "intersection_update", "difference_update", "symmetric_difference_update",
})


def _python_type_tokens(text: str) -> set[str]:
    """Split a Python type-annotation text into top-level token names.

    ``Optional[Any]`` → {Optional, Any}; ``list[int]`` → {list, int};
    ``dict[str, Any]`` → {dict, str, Any}; ``Foo | Any`` → {Foo, Any}.
    Crude but sufficient for the escape-hatch predicate.
    """
    out: set[str] = set()
    buf: list[str] = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            buf.append(ch)
        else:
            if buf:
                out.add("".join(buf))
                buf = []
    if buf:
        out.add("".join(buf))
    return out
