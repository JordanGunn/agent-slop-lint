"""``Grammar`` — the tabular per-language adapter contract.

Ported from the legacy ``slop.language.Language`` ABC. Renamed to ``Grammar``
(the component model already uses ``Realm.language`` for the id string; the
adapter is the *grammar*). It is tabular metadata + extractor classmethods —
never a walker. A ``Realm`` owns one ``Grammar``; carving and the metric layer
read it.

Faithful port (this encodes real tree-sitter / language constraints), with two
deliberate omissions, per the governing principle that legacy structure is
suspect not sacred:

- ``post_scan_adjust`` — the legacy walked generically then *rewrote* mis-parented
  Go-receiver / Rust-impl records. Carving will parent correctly by construction;
  the fixup hook should not exist.
- ``resolve_module`` — import-string → path resolution feeds the DependencyGraph,
  which is out of scope for this build.

Defaults use raw tree-sitter node-type strings (the legacy's per-category
constant modules were over-organised; a shared node vocabulary can be extracted
later if multiple grammars want it).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from ..parse import load_ts_language


class Paradigm(Enum):
    """The capability tier of a grammar — decides which typed accessors a carved
    Module/Package exposes."""

    PROCEDURAL = "procedural"            # free functions, no classes (C, Julia)
    OBJECT_ORIENTED = "object_oriented"  # classes + methods, no free functions (Java, C#)
    MULTI_PURPOSE = "multi_purpose"      # both (Python, Go, Rust, C++, Ruby, TS, JS)


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
        return frozenset({"identifier"})

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
        return frozenset({"identifier"})

    @classmethod
    def extract_parameters(cls, node: Any, content: bytes) -> tuple[tuple[str, str | None], ...]:
        """``(name, annotation)`` pairs for a callable's parameters, in order.

        Language-neutral by construction: the name is an identifier-typed node — the
        parameter node itself (a bare ``a``) or its identifier children (a typed /
        defaulted / wrapped parameter) — while *types* are distinct node kinds and so
        are excluded. This covers Python/Go/Rust/Java/TS/JS/Ruby unchanged. Grammars
        whose parameter names nest deeper (C/C++ declarators) or live elsewhere (Julia
        signatures) override this. Annotation is left ``None`` — the only caller
        (carve) uses names; string-typing for the sentinels rule is a separate fact
        (``string_annotated_parameters``)."""
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

    @classmethod
    def member_access_patterns(cls) -> tuple[tuple[str, str], ...]:
        """``(node_type, receiver_field)`` pairs for member access — ``recv.attr`` and
        ``recv[k]`` — where ``receiver_field`` is the ``child_by_field_name`` key
        holding the accessed object. Used to measure whether a parameter is treated as
        a receiver (the first-param-cluster ``missing_class`` signal). Empty default: a
        grammar with no member-access concept reports a receiver density of 0 (an honest
        "not measured"), never a mismeasurement. Every concrete grammar with member
        access overrides this — the node types are language-specific (Python
        ``attribute``, Go ``selector_expression``, Rust ``field_expression``, …), so a
        single hardcoded set would silently read 0 on every other language."""
        return ()

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
        """Numeric-literal node types (for magic-literal detection)."""
        return frozenset()

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        """Leaf node types counted as Halstead operators."""
        return frozenset()

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        """Leaf node types counted as Halstead operands."""
        return frozenset()

    # ---- mutation / sentinel / type vocabulary ------------------------

    @classmethod
    def parameter_mutations(cls, fn_node: Any, content: bytes) -> list[tuple[str, str, int]]:
        """``(param, method, line)`` for each in-place parameter mutation this language
        can detect — a fact; the rule decides what is worth flagging. Default empty."""
        del fn_node, content
        return []

    @classmethod
    def string_annotated_parameters(cls, fn_node: Any, content: bytes) -> list[tuple[str, bool]]:
        """``(param, has_string_annotation)`` pairs. Default empty."""
        del fn_node, content
        return []

    @classmethod
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        """``(query, kind)`` tree-sitter pairs capturing type annotations as ``@annotation``."""
        return ()

    @classmethod
    def is_dynamic_type(cls, text: str) -> bool:
        """True if annotation text is the language's escape-hatch type (Any/interface{}/dynamic)."""
        del text
        return False

    # ---- call-site vocabulary -----------------------------------------

    @classmethod
    def call_node_types(cls) -> frozenset[str]:
        """Node types representing a call expression."""
        return frozenset()

    @classmethod
    def extract_callee_name(cls, call_node: Any, content: bytes) -> str | None:
        """Final identifier of a call's callee, or None."""
        del call_node, content
        return None

    @classmethod
    def language_builtins(cls) -> frozenset[str]:
        """The language's builtin / stdlib callable names (a fact). Consumers decide
        whether to discount them as noise; the grammar does not."""
        return frozenset()

    # ---- reference / dispatch semantics -------------------------------

    @classmethod
    def is_dynamic_language(cls) -> bool:
        """True if the language resolves references dynamically at runtime — duck
        typing, reflection, monkey-patching, string-keyed dispatch — to a degree that
        defeats static reference counting. Lowers orphan-detection confidence: an
        apparent orphan may be reached by machinery static analysis cannot see.
        Default ``False`` (statically dispatched); the dynamic grammars override."""
        return False

    @classmethod
    def is_special_method(cls, name: str) -> bool:
        """True if ``name`` is a language-special method/symbol invoked *implicitly*
        by the runtime rather than called by name (Python's ``__dunder__``). Such a
        name looks orphaned (no explicit caller) and is not a domain-meaningful callee,
        so the orphan and sibling-redundancy signals discount it. Default ``False`` —
        most languages have no name-pattern convention for implicit dispatch; Python
        overrides with the dunder rule."""
        del name
        return False

    # ---- class / package vocabulary -----------------------------------

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        """``(query, kind)`` tree-sitter pairs capturing import module strings as ``@module``."""
        return ()

    @classmethod
    def resolve_module(cls, module: str, candidates: dict[str, Any]) -> Any | None:
        """Resolve a raw import specifier to a candidate (a module id), via the
        corpus name index. Default: exact match, then trailing segment after a
        ``.``/``::``/``/`` separator. Grammars with bespoke resolution override."""
        if module in candidates:
            return candidates[module]
        for sep in (".", "::", "/"):
            if sep in module:
                tail = module.rsplit(sep, 1)[1]
                if tail in candidates:
                    return candidates[tail]
        return None

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
        convention. Used by the runt-package signal, which is structurally N/A
        where this is ``None``."""
        return None


def _node_text(node: Any, content: bytes) -> str:
    """The source text spanned by ``node``."""
    return content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _first_identifier(node: Any, identifier_types: frozenset[str] = frozenset({"identifier"})) -> Any:
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


def c_style_parameters(node: Any, content: bytes) -> tuple[tuple[str, str | None], ...]:
    """C/C++ parameter extraction: the parameter list hangs off the function
    *declarator*, and each parameter's name nests inside its own declarator
    (``char *name`` → ``pointer_declarator`` → ``identifier``)."""
    decl = node.child_by_field_name("declarator")
    for _ in range(6):  # walk down to the function_declarator (mirrors c.py)
        if decl is None or decl.type == "function_declarator":
            break
        decl = decl.child_by_field_name("declarator")
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
        ident = child if child.type == "identifier" else _first_identifier(child)
        if ident is not None:
            out.append((_node_text(ident, content), None))
    return tuple(out)
