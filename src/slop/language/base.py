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

    # ---- Structural control-flow vocabulary (NPath) -----------------
    # Per-language node-type sets consumed by ``Structure.combinatorial``
    # (Nejmeh 1988 NPath). Where the cyclomatic vocabulary
    # (``decision_nodes``, ``nesting_nodes``) only needs to identify
    # decision points, NPath's recurrence depends on the SHAPE of each
    # branching construct (if vs loop vs switch vs try) so the walker
    # can apply the right rule: additive for alternatives, sum-over-
    # cases for switches, multiplicative across sequential statements.
    #
    # All defaults are empty / sentinel so a grammar without overrides
    # produces NPath = 1 (the base path) rather than crashing.

    @classmethod
    def if_nodes(cls) -> frozenset[str]:
        """Tree-sitter node types for ``if`` conditionals (the wrapper)."""
        return frozenset()

    @classmethod
    def elif_nodes(cls) -> frozenset[str]:
        """Tree-sitter node types for an ``elif`` / ``elseif`` clause.

        Empty when the language has no dedicated elif node and uses
        C-style nested ``else { if … }`` chains (JS, TS, Go, Rust,
        Java, C#, C, C++).
        """
        return frozenset()

    @classmethod
    def else_nodes(cls) -> frozenset[str]:
        """Tree-sitter node types for an ``else`` clause wrapper.

        Empty in grammars without an else-wrapper node (C# — see
        ``bare_else_keyword``).
        """
        return frozenset()

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        """Tree-sitter node types for loop constructs (for / while / do)."""
        return frozenset()

    @classmethod
    def switch_nodes(cls) -> frozenset[str]:
        """Tree-sitter node types for switch / match container constructs.

        May include multiple variants in one grammar (Java's classic
        ``switch_statement`` plus modern ``switch_expression``).
        """
        return frozenset()

    @classmethod
    def case_nodes(cls) -> frozenset[str]:
        """Tree-sitter node types for individual switch / match case children.

        May include multiple variants where one grammar emits
        different case shapes for different switch forms (Java:
        ``switch_label`` for ``switch_statement``, ``switch_rule``
        for ``switch_expression``).
        """
        return frozenset()

    @classmethod
    def try_nodes(cls) -> frozenset[str]:
        """Tree-sitter node types for exception-protected blocks (try / begin)."""
        return frozenset()

    @classmethod
    def catch_nodes(cls) -> frozenset[str]:
        """Tree-sitter node types for exception-handler clauses (catch / except / rescue)."""
        return frozenset()

    @classmethod
    def body_field(cls) -> str:
        """Tree-sitter field name that holds a callable / branch body.

        Most grammars use ``"body"``; Python's if-branches use
        ``"consequence"`` separately handled by the walker. Empty
        string signals a flat-body language (Julia, Ruby): statements
        are direct children of the parent rather than wrapped in a
        block, and ``body_skip_types`` enumerates the structural
        keywords to skip when walking children.
        """
        return "body"

    @classmethod
    def block_types(cls) -> frozenset[str]:
        """Tree-sitter node types that wrap a sequence of statements.

        ``block`` (Python / Go / Rust / Java / C#), ``statement_block``
        (JS / TS), ``compound_statement`` (C / C++), ``body_statement``
        (Ruby). Empty for flat-body grammars (Julia).
        """
        return frozenset()

    @classmethod
    def switch_body_types(cls) -> frozenset[str]:
        """Wrapper nodes nested between a switch and its case children.

        Java: ``switch_block`` / ``switch_block_statement_group``.
        C#: ``switch_body``. C / C++: ``compound_statement``. The
        NPath walker recurses through these to find case nodes.
        """
        return frozenset()

    @classmethod
    def body_skip_types(cls) -> frozenset[str]:
        """Child node types to skip when walking a flat-body construct.

        Only meaningful when ``body_field`` is empty — flat-body
        grammars (Julia, Ruby) emit structural keywords (``def``,
        ``end``, ``if``, ``else``, …) as direct children of the
        function / branch node and the walker filters them out.
        """
        return frozenset()

    @classmethod
    def bare_else_keyword(cls) -> str | None:
        """Bare ``else`` keyword token in grammars without an else-wrapper node.

        C# emits ``else`` as a literal keyword child of the
        ``if_statement`` followed by the else body (block or nested
        if). The NPath walker special-cases this when
        ``else_nodes`` is empty.
        """
        return None

    # ---- Type-annotation vocabulary -------------------------------
    # Tree-sitter queries that capture type-annotation text + a per-
    # language predicate identifying escape-hatch type names. Consumed
    # by ``Structure.type_annotations`` which feeds
    # ``structural.types.escape_hatches`` (fraction of annotations
    # using the language's universal escape-hatch type).

    @classmethod
    def type_annotation_queries(cls) -> tuple[tuple[str, str], ...]:
        """Tree-sitter ``(query, kind_label)`` pairs capturing type annotation nodes.

        Each query captures the annotation as ``@annotation``. Multi-
        pattern languages (e.g. Python has typed_parameter + return_type)
        declare multiple pairs. Returns empty by default — grammars
        without annotation node types (C, C++, JS, Ruby) contribute
        nothing to the escape-hatch metric.
        """
        return ()

    @classmethod
    def is_escape_hatch_text(cls, text: str) -> bool:
        """True if the annotation text represents the language's escape-hatch type.

        Python: ``Any`` (often imported from typing). TS: ``any``. Go:
        ``any`` or ``interface{}``. Rust: ``dyn Any`` / ``Box<dyn Any>``.
        Java: ``Object``. C#: ``object`` / ``dynamic``. Julia: ``Any``.
        Default returns False — every annotation classifies as concrete.
        """
        del text
        return False

    # ---- Call-site vocabulary --------------------------------------
    # Per-language identification of function calls — the node type
    # representing a call expression plus a per-language extractor for
    # the callee name. Consumed by ``Structure.callees_of`` which feeds
    # ``structural.redundancy`` (sibling-callee overlap detection) and
    # any future caller-graph analysis.

    @classmethod
    def call_node_types(cls) -> frozenset[str]:
        """Tree-sitter node types representing a function / method call.

        Most C-family grammars emit ``call_expression``; Python emits
        ``call``; Ruby emits ``call`` (and also implicit calls via bare
        identifiers, not counted here). Default empty — grammars
        without an override contribute no callee data.
        """
        return frozenset()

    @classmethod
    def extract_callee_name(cls, call_node: Any, content: bytes) -> str | None:
        """Extract the textual name of the function being called.

        Returns the final identifier of the callee — for ``obj.method()``
        returns ``method``; for ``ns::fn()`` returns ``fn``; for
        ``ptr->fn()`` returns ``fn``. Returns ``None`` for unsupported
        call shapes (e.g. call expressions on indexed access). Grammars
        without an override return ``None`` for every call.
        """
        del call_node, content
        return None

    @classmethod
    def trivial_callees(cls) -> frozenset[str]:
        """Callee names that should be filtered before overlap analysis.

        Per-language stdlib / built-in names that show up in many
        function bodies and would create spurious sibling-call overlap.
        Universal filters (length < 3, dunder names) are applied
        separately by ``Structure.callees_of``.
        """
        return frozenset()

    # ---- Package architecture vocabulary ----------------------------
    # Per-language signals consumed by ``Structure.packages`` (Martin
    # 1994 distance from the main sequence): abstractness classification
    # for individual class-like scopes + the rule for grouping files
    # into packages.
    #
    # ``is_abstract_scope`` returns a tri-state:
    #   - ``True``  → scope counts toward Na (abstract types: interfaces,
    #                 traits, Java ``abstract class``, Python ABCs)
    #   - ``False`` → scope counts toward Nc (concrete classes / structs)
    #   - ``None``  → scope is neither (skip — e.g. Go type aliases,
    #                 Rust impl_item, anonymous scopes)
    #
    # The default is ``None``: a grammar without abstractness opinions
    # contributes nothing to either Na or Nc, which puts every package
    # in that language permanently in Zone of Pain (the legacy kernel
    # behaviour for C and JavaScript).

    @classmethod
    def is_abstract_scope(cls, node: Any, content: bytes) -> bool | None:
        """Classify a class-like scope as abstract / concrete / neither.

        Receives the AST node stored in ``ParseResult.scope_nodes`` —
        whatever the grammar's ``classes()`` set matched. Default
        returns ``None`` (uncountable). Concrete grammars override.
        """
        del node, content
        return None

    @classmethod
    def resolve_packages(
        cls, root: Any, files: list[Any],
    ) -> dict[str, list[Any]]:
        """Group source files into packages by language-specific rules.

        Default: directory-grouping (every directory containing source
        files is one package). Python overrides to require an
        ``__init__.py`` per directory. Go could override for
        main-package handling; the current implementation keeps the
        default (the legacy kernel's Go path was also directory-only).

        Returns a mapping of ``package_name → file paths``. The name is
        an opaque string — typically the directory path relative to
        ``root``.
        """
        from pathlib import Path as _Path

        root_path = _Path(root)
        by_dir: dict[str, list[_Path]] = {}
        for f in files:
            fp = _Path(f)
            try:
                rel = fp.parent.resolve().relative_to(root_path.resolve())
                name = rel.as_posix() or root_path.name or "<root>"
            except ValueError:
                name = str(fp.parent)
            by_dir.setdefault(name, []).append(fp)
        return by_dir  # type: ignore[return-value]

    # ---- Import-graph vocabulary ------------------------------------
    # Tree-sitter queries that extract per-file module-import edges.
    # Each grammar emits its own import-statement shape, and the
    # interesting bit (the module-name string) is typically a nested
    # capture rather than the statement node itself — so the contract
    # is "give me a list of (query, kind_label) pairs" rather than a
    # bare frozenset of node types. The kind label flows through to
    # ``Import`` records so downstream rules can distinguish, e.g.,
    # ``include_local`` from ``include_system`` or ``require_relative``
    # from ``require``.
    #
    # See ``slop.structure._imports`` for query execution and module
    # resolution. Default is empty — a grammar without an override
    # contributes no import edges to the dependency graph.

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        """Tree-sitter ``(query, kind_label)`` pairs for extracting imports.

        Each query string is a tree-sitter S-expression that captures
        the module-name fragment as ``@module``. Multi-pattern languages
        (Python: ``import`` + ``from``; C: local + system include) declare
        several pairs. The walker runs every query against each parsed
        tree, emitting one ``Import`` record per match.

        Returns an empty tuple by default — grammars without an override
        contribute zero edges to the dependency graph.
        """
        return ()

    @classmethod
    def resolve_module(
        cls, module: str, candidates: dict[str, str],
    ) -> str | None:
        """Resolve a raw import string to an absolute file path.

        ``candidates`` is a flat module-name → abs-path index built by
        the view from the corpus. Default behaviour: try the raw module
        string, then its trailing segment (after the final ``.`` or
        ``/`` or ``::``), then the basename with common extensions
        stripped. Grammars whose import strings need language-specific
        massaging override this — e.g. C/C++ to strip ``./`` prefixes,
        Ruby to handle ``require_relative`` paths.

        Returns ``None`` if no candidate matches.
        """
        if module in candidates:
            return candidates[module]
        # Trailing segment (Python ``foo.bar`` → ``bar``; Rust ``foo::bar`` → ``bar``)
        for sep in (".", "::", "/"):
            if sep in module:
                tail = module.rsplit(sep, 1)[1]
                if tail in candidates:
                    return candidates[tail]
        return None

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
