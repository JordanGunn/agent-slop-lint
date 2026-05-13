"""``Language`` — the base grammar contract.

The abstract base class every concrete grammar implementation
satisfies. Cannot be instantiated, but all methods are classmethods —
grammar dispatch never requires construction.

Concrete grammars declare:
  - ``id`` — the language identifier (e.g. "python"); also the
    tree-sitter package suffix (``tree_sitter_python``).
  - ``callable()`` — the set of tree-sitter node types that define
    callables in this language.
  - Optionally, overrides for ``identifiers()``, ``extract_name()``,
    ``extract_parameters()`` when the language's tree-sitter conventions
    differ from the defaults.

The actual AST walking lives in ``Tree`` — grammars are tabular
metadata + extractor helpers, never iterators or walkers.

See ``docs/planning/language.md`` for the locked design.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from slop._ast.treesitter import load_language

if TYPE_CHECKING:
    from slop.tree.records import Parameter


class Language(ABC):
    """Base grammar contract — the interface every concrete grammar satisfies.

    Concrete grammars declare ``id`` (the language identifier used by
    views' ``where(language=...)`` filter AND as the tree-sitter
    package suffix) and ``callable()`` (the node types this language
    uses to define callables).
    """

    id: ClassVar[str]

    @classmethod
    def grammar(cls) -> Any:
        """The tree-sitter ``Language`` object for this grammar.

        Lazily loaded + cached by ``_ast.treesitter._LANGUAGE_CACHE``
        on first call. Calling repeatedly is O(1).
        """
        return load_language(cls.id)

    @classmethod
    @abstractmethod
    def callable(cls) -> frozenset[str]:
        """All tree-sitter node types that define callables in this language.

        The semantic discrimination between functions and methods is
        handled by ``Procedural.functions()`` / ``ObjectOriented.methods()``
        (which default to ``cls.callable()``) and by the walk's
        class-context tracking.
        """

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        """Tree-sitter node types that represent identifier tokens.

        Default ``{"identifier"}`` works for most languages. Grammars
        with field/property/type variants (Go, Cpp field_identifier;
        JS property_identifier; TS type_identifier) override this to
        widen the set.
        """
        return frozenset({"identifier"})

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Extract the name of a named node (function, class, etc.).

        Default leans on tree-sitter convention: ``child_by_field_name("name")``.
        Languages that don't follow this convention (C declarator chains,
        C++ qualified_identifier, Ruby positional def, Julia short-form)
        override this classmethod.

        Returns ``"<anonymous>"`` when no name can be extracted.
        """
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return "<anonymous>"
        return content[name_node.start_byte:name_node.end_byte].decode(
            "utf-8", errors="replace",
        )

    # ---- Control-flow vocabulary ------------------------------------
    # Tree-sitter node-type metadata consumed by the Structure view's
    # complexity computations (cyclomatic / cognitive / npath). Each
    # method returns a per-language set; defaults are empty / None so
    # a grammar that doesn't declare them contributes 0 to any metric
    # rather than crashing.

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        """Tree-sitter node types that contribute +1 to McCabe Cyclomatic Complexity.

        One entry per decision point — ``if_statement``,
        ``for_statement``, switch arms, exception clauses, ternaries.
        Each language's grammar names these differently
        (``case_clause`` vs ``switch_case`` vs ``switch_label``);
        concrete grammars override with their actual node types.
        """
        return frozenset()

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        """Tree-sitter node types that increment Cognitive Complexity nesting depth.

        Mostly overlaps with ``decision_nodes`` but typically points
        at the *container* shape (``switch_statement`` rather than
        ``switch_case``, ``match_expression`` rather than
        ``match_arm``). Default: ``cls.decision_nodes()``.
        """
        return cls.decision_nodes()

    @classmethod
    def boolean_op_node(cls) -> str | None:
        """Tree-sitter node type that hosts short-circuit boolean operators.

        Python uses a dedicated ``boolean_operator`` node; most C-family
        grammars fold ``&&``/``||`` into a generic ``binary_expression``
        and rely on operator-text filtering (see
        ``boolean_op_operators``). Return ``None`` for grammars without
        short-circuit ops.
        """
        return None

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        """Operator texts to count when ``boolean_op_node`` is a shared node type.

        ``None`` means "every instance of ``boolean_op_node`` counts"
        (Python — the node is dedicated). A frozenset filters by the
        operator text child (JS/TS/Go/Java/C/C++/C#: ``{"&&", "||"}``
        plus ``"??"`` for JS/TS).
        """
        return None

    @classmethod
    def compensating_decisions(cls) -> frozenset[str]:
        """Decision nodes that are syntactic children of a nesting container.

        Examples: Python's ``elif_clause`` lives inside ``if_statement``
        but is logically at the same level; ``switch_case`` inside
        ``switch_statement``; Rust's ``match_arm`` inside
        ``match_expression``. Cognitive Complexity uses depth-1 for
        these to compensate for the syntactic nesting that doesn't add
        logical depth.
        """
        return frozenset()

    @classmethod
    def definition_unwrap_types(cls) -> frozenset[str]:
        """Wrapper node types that the walker descends through to reach a definition.

        The canonical example is C++ ``template_declaration``, which
        wraps the actual ``function_definition`` / ``class_specifier``.
        Default: empty — no unwrapping needed (Python, JS, Go, Rust,
        Java, C#, Julia, C, Ruby).
        """
        return frozenset()

    @classmethod
    def numeric_literal_nodes(cls) -> frozenset[str]:
        """Tree-sitter node types for numeric literal values.

        Per-language: Python's ``integer`` / ``float``, Go's
        ``int_literal`` / ``float_literal``, Java's
        ``decimal_integer_literal`` family, etc. Consumed by the
        ``structural.magic_literals`` rule to find embedded numeric
        constants inside function bodies. Default empty — grammars
        that don't override contribute 0 magic-literal findings.
        """
        return frozenset()

    @classmethod
    def operator_nodes(cls) -> frozenset[str]:
        """Tree-sitter LEAF node types classified as Halstead operators.

        Includes language keywords (``if``, ``for``, ``return``,
        ``def``, ``throw``, ``new``, …) and operator-symbol tokens
        (``=``, ``+``, ``==``, ``&&``, ``<-``, …). Tree-sitter
        commonly assigns these tokens a ``node.type`` equal to their
        source text, which is what this set matches against.

        Consumed by Halstead vocabulary computations
        (``structural.difficulty.volume`` and ``.density``). Default
        empty — grammars without an override contribute 0 to the
        operator count.
        """
        return frozenset()

    @classmethod
    def operand_nodes(cls) -> frozenset[str]:
        """Tree-sitter LEAF node types classified as Halstead operands.

        Identifier-like leaves (``identifier``, ``property_identifier``,
        ``field_identifier``) and literal-like leaves (``integer``,
        ``float``, ``string``, ``true``, ``false``, ``null``).

        Consumed by Halstead vocabulary computations. Default empty
        — grammars without an override contribute 0 to the operand
        count.
        """
        return frozenset()

    @classmethod
    def extract_superclasses(cls, node: Any, content: bytes) -> list[str]:
        """Extract base-class / interface names from a class-shaped node.

        Each grammar exposes inheritance differently: Python's
        ``superclasses`` field; Java's ``superclass`` field plus
        ``interfaces`` for implements; C#'s ``base_list`` child;
        TypeScript's ``class_heritage`` with ``extends_clause`` and
        ``implements_clause``; C++'s ``base_class_clause`` direct
        child; Ruby's positional identifier after ``<``; Go uses
        struct embedding (handled in ``post_scan_adjust``); Rust uses
        impl-based pseudo-inheritance (also handled there).

        Consumed by CK class metrics (WMC sums method CCX,
        CBO references inheritance, DIT walks parent chain, NOC
        counts subclasses). Default returns empty list — grammars
        without inheritance contribute 0 to DIT / NOC and don't
        boost CBO via parent links.
        """
        del node, content  # default no-op; concrete grammars override
        return []

    @classmethod
    def post_scan_adjust(cls, parse_result: Any) -> Any:
        """Post-scan hook for language-specific record rewriting.

        Called once per file by ``Tree._scan_file`` after the generic
        walker has emitted scopes, callables, and occurrences. The
        default returns the parse_result unchanged.

        Override on grammars where the canonical structure-emitting
        walk needs language-specific fix-up:

          - Go: ``method_declaration`` callables should be parented to
            their receiver type (struct), not to the file/module
            scope. The override rewrites the relevant Callable
            records to set the correct parent.

          - Rust: ``function_item`` callables nested inside an
            ``impl_item`` should be parented to the impl's target
            type. The override walks impl_items and rewrites the
            nested callables' parents.

        Other grammars don't need post-scan adjustment.
        """
        return parse_result

    @classmethod
    def extract_parameters(cls, node: Any, content: bytes) -> tuple[Parameter, ...]:
        """Extract parameters from a callable definition node.

        Default walks the ``parameters`` field and processes each child
        node by type (identifier, typed_parameter, default_parameter,
        list_splat_pattern, dictionary_splat_pattern). Languages whose
        parameter syntax differs significantly override this method.
        """
        from slop.tree.records import Parameter

        params_node = node.child_by_field_name("parameters")
        if params_node is None:
            return ()
        out: list[Parameter] = []
        position = 0
        for child in params_node.children:
            ctype = child.type
            if ctype in ("(", ")", ",", "*", "**", "/", "=", "lambda"):
                continue
            param_name, annotation = _default_parameter_parts(child, content)
            if param_name is None:
                continue
            out.append(Parameter(name=param_name, position=position, annotation=annotation))
            position += 1
        return tuple(out)


def _default_parameter_parts(node: Any, content: bytes) -> tuple[str | None, str | None]:
    """Default (name, annotation) extraction for one parameter node.

    Handles the common tree-sitter parameter shapes:
      - identifier
      - typed_parameter / typed_default_parameter
      - default_parameter
      - list_splat_pattern (*args) / dictionary_splat_pattern (**kwargs)
    """
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
        annotation = None
        if type_node is not None:
            annotation = content[type_node.start_byte:type_node.end_byte].decode(
                "utf-8", errors="replace",
            ).strip()
        return (name, annotation)
    if ntype == "default_parameter":
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            return (
                content[name_node.start_byte:name_node.end_byte].decode(
                    "utf-8", errors="replace",
                ),
                None,
            )
        return (None, None)
    if ntype in ("list_splat_pattern", "dictionary_splat_pattern"):
        for c in node.children:
            if c.type == "identifier":
                prefix = "*" if ntype == "list_splat_pattern" else "**"
                return (
                    prefix
                    + content[c.start_byte:c.end_byte].decode("utf-8", errors="replace"),
                    None,
                )
        return (None, None)
    return (None, None)
