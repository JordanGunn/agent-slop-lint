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
    def extract_parameters(cls, node: Any, content: bytes) -> tuple[tuple[str, str | None], ...]:
        """``(name, annotation)`` pairs for a callable's parameters (in order)."""
        params_node = node.child_by_field_name("parameters")
        if params_node is None:
            return ()
        out: list[tuple[str, str | None]] = []
        for child in params_node.children:
            if child.type in ("(", ")", ",", "*", "**", "/", "=", "lambda"):
                continue
            name, annotation = _default_parameter_parts(child, content)
            if name is None:
                continue
            out.append((name, annotation))
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


def _default_parameter_parts(node: Any, content: bytes) -> tuple[str | None, str | None]:
    """Default ``(name, annotation)`` extraction for one parameter node (Python-shaped)."""
    ntype = node.type
    if ntype == "identifier":
        return (content[node.start_byte:node.end_byte].decode("utf-8", errors="replace"), None)
    if ntype in ("typed_parameter", "typed_default_parameter"):
        name = None
        for c in node.children:
            if c.type == "identifier":
                name = content[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
                break
        type_node = node.child_by_field_name("type")
        annotation = (
            content[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace").strip()
            if type_node is not None else None
        )
        return (name, annotation)
    if ntype == "default_parameter":
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            return (content[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace"), None)
        return (None, None)
    if ntype in ("list_splat_pattern", "dictionary_splat_pattern"):
        for c in node.children:
            if c.type == "identifier":
                prefix = "*" if ntype == "list_splat_pattern" else "**"
                return (prefix + content[c.start_byte:c.end_byte].decode("utf-8", errors="replace"), None)
        return (None, None)
    return (None, None)
