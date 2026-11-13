"""Python grammar: classes, free functions and lambdas."""
from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from .interface import Grammar, MemberAccess
from .imports import ModuleIndex, distinct
from .heritage import heritage


class Python(Grammar):
    id: ClassVar[str] = "python"

    @classmethod
    def hoisted_bindings(cls) -> bool:
        return True

    @classmethod
    def is_special_method(cls, name: str) -> bool:
        return name.startswith("__") and name.endswith("__")

    @classmethod
    def implicit_receiver_names(cls) -> frozenset[str]:
        return frozenset({"self", "cls"})

    @classmethod
    def member_access(cls) -> tuple[MemberAccess, ...]:
        return (MemberAccess("attribute", "object", "attribute"),)

    @classmethod
    def instance_receiver(cls, method: Any, content: bytes) -> str | None:
        """The method's first parameter, unless it is decorated ``staticmethod`` or
        ``classmethod`` or is named ``cls`` (``__init_subclass__`` and metaclass methods
        take the class, not an instance)."""
        if _has_non_instance_decorator(method, content):
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
    def string_literal_nodes(cls) -> frozenset[str]:
        return frozenset({"string"})

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
    def import_names(cls, node: Any) -> tuple[str, ...]:
        """``from X import a, b as c`` takes ``a`` and ``b`` from ``X``; either may be a submodule."""
        statement = node.parent
        if statement is None or statement.type != "import_from_statement":
            return ()
        names = []
        for child in statement.children():
            if child.type == "dotted_name" and child.text != node.text:
                names.append(child.text)
            elif child.type == "aliased_import" and child.field("name") is not None:
                names.append(child.field("name").text)
        return tuple(names)

    @classmethod
    def resolve_import(cls, decl: Any, importer: Path, index: ModuleIndex) -> tuple[Any, ...]:
        """The modules the code takes something from: each imported name that is a submodule,
        and the named module itself when it supplies anything else (an attribute, ``*``, or
        the whole module in ``import x``). ``from . import a`` therefore depends on ``a``, not
        on the package. Leading dots anchor at the importer's package, one more level up per
        dot; an absolute name must match a module path exactly, never by its last segment
        alone, so ``os.path`` cannot resolve to a local ``path.py``."""
        spec = decl.specifier
        dots = len(spec) - len(spec.lstrip("."))
        if dots == 0:
            def lookup(spelling: str) -> Any | None:
                return index.by_name.get(spelling)
            submodules = [lookup(f"{spec}.{name}") for name in decl.names]
            container = spec
        else:
            base = importer.parent
            for _ in range(dots - 1):
                base = base.parent
            module = base.joinpath(*spec[dots:].split(".")) if spec[dots:] else base

            def lookup(place: Path) -> Any | None:
                return index.at(place) or index.at(place / "__init__")
            submodules = [lookup(module / name) for name in decl.names]
            container = module
        takes_attribute = not decl.names or None in submodules
        return distinct([*submodules, lookup(container) if takes_attribute else None])

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """The base classes in ``class C(A, mod.B, Store[int], metaclass=M)``: ``A``, ``B``, ``Store``."""
        return heritage(node, content, ("argument_list",))

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
        by_dir = super().resolve_packages(root, files)
        return {
            name: dir_files
            for name, dir_files in by_dir.items()
            if any(Path(f).name == "__init__.py" for f in dir_files)
        }

    @classmethod
    def package_init_name(cls) -> str | None:
        return "__init__.py"


def _has_non_instance_decorator(method: Any, content: bytes) -> bool:
    parent = method.parent
    if parent is None or parent.type != "decorated_definition":
        return False
    for decorator in parent.children:
        if decorator.type != "decorator":
            continue
        text = content[decorator.start_byte:decorator.end_byte].decode()
        if text.lstrip("@").split("(")[0].strip().split(".")[-1] in {"staticmethod", "classmethod"}:
            return True
    return False
