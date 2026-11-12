"""``Grammar`` — the tabular per-language adapter contract.

Ported from the legacy ``slop.language.Language`` ABC. Renamed to ``Grammar``
(the component model already uses ``Realm.language`` for the id string; the
adapter is the *grammar*). It is tabular metadata + extractor classmethods —
never a walker. A ``Realm`` owns one ``Grammar``; carving and the metric layer
read it.

Faithful port (this encodes real tree-sitter / language constraints), with one
deliberate omission, per the governing principle that legacy structure is
suspect not sacred:

- ``post_scan_adjust`` — the legacy walked generically then *rewrote* mis-parented
  Go-receiver / Rust-impl records. Carving will parent correctly by construction;
  the fixup hook should not exist.

Defaults use raw tree-sitter node-type strings (the legacy's per-category
constant modules were over-organised; a shared node vocabulary can be extracted
later if multiple grammars want it).
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from collections.abc import Iterable
from typing import Any, ClassVar

from ..parse import load_ts_language


_IDENTIFIER = "identifier"


def _normal(path: Path) -> Path:
    """``path`` with ``.`` and ``..`` collapsed, without touching the filesystem."""
    return Path(os.path.normpath(path))


@dataclass(frozen=True)
class ModuleIndex:
    """The corpus's modules, as an import can name them: ``by_name`` holds every spelling a
    module path can take (``find``, ``scope.find``, ``scope/find``, ...), ``by_path`` the
    module's file, with and without its suffix. Values are module ids."""

    by_name: dict[str, Any]
    by_path: dict[Path, Any]

    def at(self, path: Path) -> Any | None:
        """The module whose file is ``path`` (or ``path`` plus a suffix), else None."""
        return self.by_path.get(_normal(path))

    @staticmethod
    def keys(file: Path) -> tuple[Path, Path]:
        """The ``by_path`` keys of a module's file."""
        return _normal(file), _normal(file).with_suffix("")


def distinct(found: Iterable[Any]) -> tuple[Any, ...]:
    """The modules in ``found``, first occurrence kept, misses (None) dropped."""
    return tuple(dict.fromkeys(m for m in found if m is not None))


class Paradigm(Enum):
    """The capability tier of a grammar — decides which typed accessors a carved
    Module/Package exposes."""

    PROCEDURAL = "procedural"            # free functions, no classes (no shipped grammar)
    OBJECT_ORIENTED = "object_oriented"  # classes + methods, no free functions (Java, C#)
    MULTI_PURPOSE = "multi_purpose"      # both (Python, Go, Rust, C, C++, Julia, Ruby, TS, JS)


@dataclass(frozen=True)
class MemberAccess:
    """A grammar's spelling of ``receiver.member``: the node type, and the fields that
    hold the receiver expression and the member name."""

    node_type: str
    receiver_field: str
    member_field: str


class Grammar(ABC):
    """Base grammar contract. Concrete grammars set ``id`` + ``PARADIGM`` and
    override the metadata/extractors that differ from these defaults."""

    id: ClassVar[str]
    PARADIGM: ClassVar[Paradigm]

    @classmethod
    def ts_language(cls) -> object | None:
        """The cached ``tree_sitter.Language`` for this grammar."""
        return load_ts_language(cls.id)

    # ---- declarations -------------------------------------------------

    @classmethod
    @abstractmethod
    def callable(cls) -> frozenset[str]:
        """Node types that define callables in this language."""

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        """Node types representing identifier tokens. Default ``{identifier}``."""
        return frozenset({_IDENTIFIER})

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Name of a named node; default uses the ``name`` field. ``<anonymous>`` if absent."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return "<anonymous>"
        return content[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")

    @classmethod
    def parameter_list_field(cls) -> str:
        """The field on a callable node holding its parameter list. Default
        ``"parameters"`` (Python/Go/Rust/Java/TS/JS/Ruby); C/C++ nest it under the
        function declarator and override ``extract_parameters`` outright."""
        return "parameters"

    @classmethod
    def parameter_name_node_types(cls) -> frozenset[str]:
        """Node types that *are* a parameter name (as opposed to a type). Default
        ``{"identifier"}`` — types are distinct node kinds (``type_identifier``,
        ``primitive_type``, ``type_annotation``, …), so identifier-typed nodes are the
        names across most grammars."""
        return frozenset({_IDENTIFIER})

    @classmethod
    def extract_parameters(cls, node: Any, content: bytes) -> tuple[tuple[str, str | None], ...]:
        """``(name, annotation)`` pairs for a callable's parameters, in order.

        Language-neutral by construction: the name is an identifier-typed node — the
        parameter node itself (a bare ``a``) or its identifier children (a typed /
        defaulted / wrapped parameter) — while *types* are distinct node kinds and so
        are excluded. This covers Python/Go/Rust/Java/TS/JS/Ruby unchanged. Grammars
        whose parameter names nest deeper (C/C++ declarators) or live elsewhere (Julia
        signatures) override this. Annotation is left ``None`` — the only caller
        (carve) uses names."""
        plist = node.child_by_field_name(cls.parameter_list_field())
        if plist is None:
            return ()
        names = cls.parameter_name_node_types()
        out: list[tuple[str, str | None]] = []
        for pnode in plist.children:
            if pnode.type in names:
                out.append((_node_text(pnode, content), None))
            else:
                for child in pnode.children:
                    if child.type in names:
                        out.append((_node_text(child, content), None))
        return tuple(out)

    # ---- cyclomatic / cognitive vocabulary ----------------------------

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        """Node types that add +1 to McCabe cyclomatic complexity."""
        return frozenset()

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        """Node types that increment cognitive-complexity nesting. Default: decision_nodes."""
        return cls.decision_nodes()

    @classmethod
    def boolean_op_node(cls) -> str | None:
        """Node type hosting short-circuit boolean operators, or None."""
        return None

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        """Operator texts to count when ``boolean_op_node`` is shared; None = count all."""
        return None

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        """Decision nodes syntactically nested in a container (elif/case) — depth-1 in cognitive."""
        return frozenset()

    @classmethod
    def definition_unwrap_types(cls) -> frozenset[str]:
        """Wrapper nodes the walker descends through to reach a definition (C++ template_declaration)."""
        return frozenset()

    # ---- npath structural vocabulary ----------------------------------

    @classmethod
    def if_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement"})

    @classmethod
    def elif_nodes(cls) -> frozenset[str]:
        return frozenset()

    @classmethod
    def else_nodes(cls) -> frozenset[str]:
        return frozenset({"else_clause"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset()

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        return frozenset()

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        return frozenset()

    @classmethod
    def try_nodes(cls) -> frozenset[str]:
        return frozenset({"try_statement"})

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        return frozenset({"catch_clause"})

    @classmethod
    def body_field(cls) -> str:
        """Field holding a callable/branch body. Empty string = flat-body language."""
        return "body"

    @classmethod
    def block_types(cls) -> frozenset[str]:
        """Node types wrapping a statement sequence."""
        return frozenset()

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        """Wrapper nodes between a switch and its cases."""
        return frozenset()

    @classmethod
    def body_skip_types(cls) -> frozenset[str]:
        """Child node types to skip when walking a flat-body construct."""
        return frozenset()

    @classmethod
    def bare_else_keyword(cls) -> str | None:
        """Bare ``else`` keyword token for grammars without an else-wrapper (C#)."""
        return None

    # ---- halstead -----------------------------------------------------

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        """Numeric-literal node types."""
        return frozenset()

    @classmethod
    def string_literal_nodes(cls) -> frozenset[str]:
        """String-literal node types: one node per literal, quotes included."""
        return frozenset()

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        """Leaf node types counted as Halstead operators."""
        return frozenset()

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        """Leaf node types counted as Halstead operands."""
        return frozenset()

    # ---- call-site vocabulary -----------------------------------------

    @classmethod
    def call_node_types(cls) -> frozenset[str]:
        """Node types representing a call expression."""
        return frozenset()

    @classmethod
    def language_builtins(cls) -> frozenset[str]:
        """The language's builtin / stdlib callable names (a fact). Consumers decide
        whether to discount them as noise; the grammar does not."""
        return frozenset()

    # ---- reference / dispatch semantics -------------------------------

    @classmethod
    def is_special_method(cls, name: str) -> bool:
        """True if ``name`` is a language-special method/symbol invoked *implicitly*
        by the runtime rather than called by name (Python's ``__dunder__``). Such a
        name is not a domain-meaningful declared name. Default ``False``: most
        languages have no name-pattern convention for implicit dispatch; Python
        overrides with the dunder rule."""
        del name
        return False

    @classmethod
    def implicit_receiver_names(cls) -> frozenset[str]:
        """Parameter names that are the implicit receiver rather than a chosen name
        (Python's ``self`` / ``cls``, which its grammar lists among a method's parameters).
        Default empty: most grammars do not list the receiver as a parameter at all."""
        return frozenset()

    @classmethod
    def class_scope_visible(cls) -> bool:
        """Whether a method sees the names its class body declares without a receiver: a bare
        ``x`` meaning ``this.x`` (Java, C#, C++) or a bare ``helper`` calling ``self.helper``
        (Ruby). False where a member is always reached through the receiver (Python,
        JavaScript, TypeScript, Go, Rust), and where there are no methods (C, Julia)."""
        return False

    @classmethod
    def hoisted_bindings(cls) -> bool:
        """Whether a name bound anywhere in a scope is bound throughout it: Python (an
        assignment makes a name local to the whole function), JavaScript and TypeScript
        (hoisting), Julia. False where a name is bound from its declaration on (Java, C#, C,
        C++, Go, Rust, and Ruby, where a bare name before its assignment is a method call)."""
        return False

    # ---- instance members (cohesion) ------------------------------------
    #
    # Cohesion asks which instance members each method touches. A member reached through
    # the instance is read here (``receiver.member``); a bare name that means a member
    # (Java's ``x`` for ``this.x``) is read from name binding (``slop.ast.binding``).

    @classmethod
    def member_access(cls) -> tuple[MemberAccess, ...]:
        """The spellings of ``receiver.member`` (Java has two: a field and a method call).
        Empty where the language has no instance members."""
        return ()

    @classmethod
    def instance_receiver(cls, method: Any, content: bytes) -> str | None:
        """What ``method`` (a raw tree-sitter node) calls its own instance: Python's first
        parameter (``self``), JavaScript's ``this``. ``None`` for a method with no instance
        (static, class method), which therefore has no instance members to share."""
        del method, content
        return None

    @classmethod
    def constructor_names(cls) -> frozenset[str]:
        """Method names that construct the instance. A constructor touches every member it
        initialises, so it would join every method into one group and hide a split."""
        return frozenset()

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        """``(query, kind)`` tree-sitter pairs capturing import module strings as ``@module``."""
        return ()

    @classmethod
    def import_names(cls, node: Any) -> tuple[str, ...]:
        """The names an import statement takes from the module ``node`` captured, where one
        of them can itself be a module (Python's ``from pkg import mod``). Default: none."""
        del node
        return ()

    @classmethod
    def resolve_import(cls, decl: Any, importer: Path, index: ModuleIndex) -> tuple[Any, ...]:
        """The corpus modules an import (an ``ImportDecl``) in the file ``importer`` loads.

        Default, for specifiers that name a module wherever it sits: an exact spelling, else
        the trailing segment after a ``.``/``::``/``/`` separator. A grammar whose language
        has file-relative imports overrides this to anchor them at ``importer``: a relative
        specifier names one place, so it never falls back to a bare-name match."""
        del importer
        spec = decl.specifier
        if spec in index.by_name:
            return (index.by_name[spec],)
        for sep in (".", "::", "/"):
            if sep in spec:
                tail = spec.rsplit(sep, 1)[1]
                if tail in index.by_name:
                    return (index.by_name[tail],)
        return ()

    @classmethod
    def resolve_packages(cls, root: Path, files: list[Path]) -> dict[str, list[Path]]:
        """Group files into packages by language rule. Default: one package per directory."""
        root_path = Path(root)
        by_dir: dict[str, list[Path]] = {}
        for f in files:
            fp = Path(f)
            try:
                rel = fp.parent.resolve().relative_to(root_path.resolve())
                name = rel.as_posix() or root_path.name or "<root>"
            except ValueError:
                name = str(fp.parent)
            by_dir.setdefault(name, []).append(fp)
        return by_dir

    @classmethod
    def package_init_name(cls) -> str | None:
        """The filename whose presence makes a directory a package (e.g. Python's
        ``__init__.py``), or ``None`` for languages with no init-file package
        convention. Used when carving packages and resolving imports."""
        return None


def _node_text(node: Any, content: bytes) -> str:
    """The source text spanned by ``node``."""
    return content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _first_identifier(node: Any, identifier_types: frozenset[str] = frozenset({_IDENTIFIER})) -> Any:
    """DFS for the first identifier-typed descendant (the name buried in a C/C++
    declarator: ``char *name`` → ``pointer_declarator`` → ``identifier``)."""
    if node is None:
        return None
    stack = [node]
    while stack:
        n = stack.pop(0)
        if n.type in identifier_types:
            return n
        stack.extend(n.children)
    return None


def _child_of_type(node: Any, type_name: str) -> Any:
    if node is None:
        return None
    for child in node.children:
        if child.type == type_name:
            return child
    return None


def has_keyword(node: Any, content: bytes, child_type: str, keyword: str) -> bool:
    """Whether a direct child of ``node`` typed ``child_type`` reads ``keyword`` (C#'s ``modifier``
    or C++'s ``storage_class_specifier`` reading ``static``)."""
    return any(c.type == child_type and content[c.start_byte:c.end_byte].decode("utf-8", errors="replace") == keyword
               for c in node.children)


def type_specifier_name(node: Any, content: bytes) -> str:
    """A C/C++ struct/union/enum/class specifier's tag, else the name of the ``typedef``
    that wraps an anonymous one (``typedef struct { ... } Point;`` is ``Point``)."""
    name = node.child_by_field_name("name")
    if name is None and node.parent is not None and node.parent.type == "type_definition":
        name = node.parent.child_by_field_name("declarator")
    if name is None or name.type not in ("type_identifier", _IDENTIFIER):
        return "<anonymous>"
    return content[name.start_byte:name.end_byte].decode("utf-8", errors="replace")


def _c_function_declarator(node: Any) -> Any | None:
    decl = node.child_by_field_name("declarator")
    for _ in range(6):  # walk down to the function_declarator (mirrors c.py)
        if decl is None or decl.type == "function_declarator":
            break
        decl = decl.child_by_field_name("declarator")
    return decl


def c_style_parameters(node: Any, content: bytes) -> tuple[tuple[str, str | None], ...]:
    """C/C++ parameter extraction: the parameter list hangs off the function
    *declarator*, and each parameter's name nests inside its own declarator
    (``char *name`` → ``pointer_declarator`` → ``identifier``)."""
    decl = _c_function_declarator(node)
    if decl is None or decl.type != "function_declarator":
        return ()
    plist = decl.child_by_field_name("parameters") or _child_of_type(decl, "parameter_list")
    if plist is None:
        return ()
    out: list[tuple[str, str | None]] = []
    for pnode in plist.children:
        if pnode.type != "parameter_declaration":
            continue
        ident = _first_identifier(pnode.child_by_field_name("declarator") or pnode)
        if ident is not None:
            out.append((_node_text(ident, content), None))
    return tuple(out)


def julia_signature_parameters(node: Any, content: bytes) -> tuple[tuple[str, str | None], ...]:
    """Julia parameter extraction: params live under ``signature → call_expression →
    argument_list`` as identifiers (or the first identifier of a typed argument)."""
    sig = _child_of_type(node, "signature")
    call = _child_of_type(sig, "call_expression") if sig is not None else None
    arglist = _child_of_type(call, "argument_list") if call is not None else None
    if arglist is None:
        return ()
    out: list[tuple[str, str | None]] = []
    for child in arglist.children:
        if child.type in ("(", ")", ","):
            continue
        ident = child if child.type == _IDENTIFIER else _first_identifier(child)
        if ident is not None:
            out.append((_node_text(ident, content), None))
    return tuple(out)
