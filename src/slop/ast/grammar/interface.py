"""The grammar's interface: what slop reads from a language's tree-sitter grammar.

``Grammar`` is the contract each language implements (``slop.ast.grammar.<language>``);
``MemberAccess`` is the record its ``member_access()`` returns.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from ..parse import load_ts_language
from .imports import ModuleIndex
from .syntax import IDENTIFIER, node_text


@dataclass(frozen=True)
class MemberAccess:
    """A grammar's spelling of ``receiver.member``: the node type, and the fields that
    hold the receiver expression and the member name."""

    node_type: str
    receiver_field: str
    member_field: str


class Grammar(ABC):
    """What slop needs to know about one language: which tree-sitter node types are callables,
    classes, decisions, literals and imports; how names, parameters, members and imports are
    spelled; and how packages are laid out. Each language's grammar sets ``id`` and overrides the
    defaults that differ for it. Everything is a class method: a grammar is a table, not a
    walker."""

    id: ClassVar[str]

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
        return frozenset({IDENTIFIER})

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
        return frozenset({IDENTIFIER})

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
                out.append((node_text(pnode, content), None))
            else:
                for child in pnode.children:
                    if child.type in names:
                        out.append((node_text(child, content), None))
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

    # ---- classes ------------------------------------------------------

    @classmethod
    @abstractmethod
    def classes(cls) -> frozenset[str]:
        """Node types defining class-like scopes (classes, structs, interfaces, enums)."""

    @classmethod
    def is_class_definition(cls, node: Any) -> bool:
        """True if a node of a ``classes()`` type *defines* a type here. Default True.

        C overrides it because ``struct_specifier`` is both a definition (has a body) and
        a type reference (``struct Node *head;``, a forward declaration)."""
        del node
        return True

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        """Classify a class-like scope abstract/concrete/neither (None). Default None."""
        del node, content
        return None

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """Base-class / interface names declared on a class node. Default empty."""
        del node, content
        return []

    @classmethod
    def reparent_callable(cls, node: Any, content: bytes) -> str | None:
        """Simple name of the type a callable structurally belongs to, when the
        grammar emits it outside that type's body (Go receiver methods, Rust impl
        functions). Carving attaches it to the matching class. Default None."""
        del node, content
        return None
