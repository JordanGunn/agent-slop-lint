"""Structure view — the substrate structural rules consume.

A ``Structure`` is a windowed view over the parsed corpus exposing
scopes, callables, and the parent/child relationships between them.

The view owns metric computations. Rules call methods like
``cyclomatic(c)``; AST walking happens inside the view, hidden behind
the compute API. See ``docs/planning/codebase.md`` for the locked
views-own-compute principle.

Slicing methods (``under``, ``where``) return NEW ``Structure``
instances over the same underlying parse data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable as TypingCallable, Iterable, Sequence

from slop.language.grammars import LANGUAGE_BY_ID
from slop.tree.records import Callable, CallableKind, ParseResult, Scope, ScopeKind


class Structure:
    """View over the corpus exposing scopes + callables + compute methods."""

    def __init__(
        self,
        parses: Sequence[ParseResult],
        *,
        filters: Sequence[TypingCallable[[Any], bool]] = (),
    ) -> None:
        self._parses = tuple(parses)
        self._filters = tuple(filters)

        # Per-callable indexes keyed by (path, qualname) — a bare qualname
        # like ``a.f`` collides across same-file-stem corpora (a.py + a.js
        # both yield ``a.f``); pairing it with the absolute path scopes
        # the lookup to its source file.
        self._language_by_path: dict[str, str] = {}
        self._callables_by_key: dict[tuple[str, str], Callable] = {}
        self._node_by_key: dict[tuple[str, str], Any] = {}
        self._content_by_key: dict[tuple[str, str], bytes] = {}
        # Class scope → AST node (for CK metrics + future scope-aware rules).
        self._scope_node_by_key: dict[tuple[str, str], Any] = {}

        for p in parses:
            self._language_by_path[str(p.path)] = p.language
            for c in p.callables:
                key = (str(c.path), c.qualname)
                self._callables_by_key[key] = c
                if c.qualname in p.callable_nodes:
                    self._node_by_key[key] = p.callable_nodes[c.qualname]
                    self._content_by_key[key] = p.content
            for s in p.scopes:
                if s.qualname in p.scope_nodes:
                    self._scope_node_by_key[(str(s.path), s.qualname)] = p.scope_nodes[s.qualname]

    # ---- iteration ---------------------------------------------------

    def scopes(self) -> Iterable[Scope]:
        for p in self._parses:
            for s in p.scopes:
                if all(f(s) for f in self._filters):
                    yield s

    def callables(self) -> Iterable[Callable]:
        for p in self._parses:
            for c in p.callables:
                if all(f(c) for f in self._filters):
                    yield c

    # ---- lookup ------------------------------------------------------

    def scope(self, qualname: str) -> Scope | None:
        for p in self._parses:
            for s in p.scopes:
                if s.qualname == qualname:
                    return s
        return None

    def children(self, scope: str) -> Iterable[Callable]:
        for c in self.callables():
            if c.parent == scope:
                yield c

    def language_for(self, record: Any) -> str | None:
        """Resolve a record's language via the internal path→language index.

        Records dropped their denormalised ``language`` field in the
        v2 refactor; views maintain the canonical mapping.
        """
        path = getattr(record, "path", None)
        if path is None:
            return None
        return self._language_by_path.get(str(path))

    # ---- compute methods (views own metric computations) -------------

    def cyclomatic(self, c: Callable) -> int:
        """McCabe cyclomatic complexity for one callable.

        Counts decision points + short-circuit boolean operators, plus
        1 for the base path (McCabe 1976: CCX = decisions + 1).

        Per-language node types come from the ``Language`` class via
        ``decision_nodes()``, ``boolean_op_node()``, and
        ``boolean_op_operators()``. ``definition_unwrap_types`` is
        honoured so C++ ``template_declaration`` wrappers descend to
        the actual function body. Languages whose grammar doesn't
        declare ``decision_nodes`` return CCX=1 (the base path).
        """
        key = (str(c.path), c.qualname)
        node = self._node_by_key.get(key)
        if node is None:
            return 1
        content = self._content_by_key.get(key)
        if content is None:
            return 1
        language_id = self._language_by_path.get(str(c.path))
        if language_id is None:
            return 1
        lang = LANGUAGE_BY_ID.get(language_id)
        if lang is None:
            return 1
        decision_nodes = lang.decision_nodes()
        if not decision_nodes:
            return 1
        walk_from = _resolve_body(node, lang.definition_unwrap_types())
        count = _count_decisions(
            walk_from,
            decision_nodes,
            lang.boolean_op_node(),
            lang.boolean_op_operators(),
            lang.callable(),
            content,
        )
        return count + 1

    def combinatorial(self, c: Callable) -> int:
        """NPath — acyclic execution path count for one callable (Nejmeh 1988).

        Counts the number of independent execution paths through the
        callable body. Unlike McCabe's CCX (additive: decisions + 1),
        NPath is multiplicative — sequential branching structures
        multiply path counts, capturing the combinatorial explosion
        that CCX flattens.

        Recurrence (Nejmeh 1988, CACM):
          - sequence:        product of statement NPs
          - if/elif/else:    sum of branch NPs (+1 for implicit
                             fall-through if no terminal else)
          - while / for:     NP(body) + 1
          - switch/match:    sum of case NPs (>= 1)
          - try / catch:     NP(try-body) + sum NP(catch-bodies)
          - nested callable: 1 (each has its own metric)

        Per-language node types come from the ``Language`` class via
        ``if_nodes()`` / ``elif_nodes()`` / ``else_nodes()`` /
        ``loop_nodes()`` / ``switch_nodes()`` / ``case_nodes()`` /
        ``try_nodes()`` / ``catch_nodes()`` / ``block_types()`` /
        ``switch_body_types()`` / ``body_skip_types()`` /
        ``body_field()`` / ``bare_else_keyword()``. C++
        ``template_declaration`` wrappers are descended through via
        ``definition_unwrap_types()``. Grammars without a structural
        vocabulary return NP = 1 (the base path).
        """
        key = (str(c.path), c.qualname)
        node = self._node_by_key.get(key)
        if node is None:
            return 1
        language_id = self._language_by_path.get(str(c.path))
        if language_id is None:
            return 1
        lang = LANGUAGE_BY_ID.get(language_id)
        if lang is None:
            return 1
        vocab = _NPathVocab.for_language(lang)
        node = _unwrap_definition(node, vocab.definition_unwrap_types)
        return max(1, _npath_walk(node, vocab))

    def cognitive(self, c: Callable) -> int:
        """Cognitive Complexity for one callable (Campbell 2018).

        Differs from cyclomatic in three ways:

          1. **Nesting penalty.** Each decision point inside a nesting
             container adds ``1 + depth`` (instead of just 1). Deeply
             nested branches cost more than flat ones.
          2. **Compensating decisions.** Syntactic children of a
             nesting container that are logically peers (``elif_clause``
             of ``if_statement``, ``switch_case`` of ``switch_statement``)
             add ``1 + max(0, depth - 1)`` — they don't double-charge
             for the parent's nesting bump.
          3. **Sequence collapsing on boolean operators.** A short-
             circuit operator counts +1 only when it isn't continuing a
             same-operator chain (``a && b && c`` contributes 1, not 2;
             ``a && b || c`` contributes 2).

        Per-language node sets come from the ``Language`` class via
        ``decision_nodes()``, ``nesting_nodes()``,
        ``compensating_decisions()``, ``boolean_op_node()``, and
        ``boolean_op_operators()``.
        """
        key = (str(c.path), c.qualname)
        node = self._node_by_key.get(key)
        if node is None:
            return 0
        content = self._content_by_key.get(key)
        if content is None:
            return 0
        language_id = self._language_by_path.get(str(c.path))
        if language_id is None:
            return 0
        lang = LANGUAGE_BY_ID.get(language_id)
        if lang is None:
            return 0
        decision_nodes = lang.decision_nodes()
        if not decision_nodes:
            return 0
        walk_from = _resolve_body(node, lang.definition_unwrap_types())
        return _cognitive_walk(
            walk_from,
            decision_nodes,
            lang.nesting_nodes(),
            lang.compensating_decisions(),
            lang.boolean_op_node(),
            lang.boolean_op_operators(),
            lang.callable(),
            content,
        )

    # ---- class-level (CK) compute methods ----------------------------

    _CLASS_KINDS: frozenset = frozenset({
        ScopeKind.CLASS, ScopeKind.INTERFACE, ScopeKind.STRUCT,
        ScopeKind.TRAIT, ScopeKind.IMPL,
    })

    def classes(self) -> Iterable[Scope]:
        """Iterate scopes whose kind is class-like (CLASS/INTERFACE/STRUCT/TRAIT/IMPL)."""
        for s in self.scopes():
            if s.kind in self._CLASS_KINDS:
                yield s

    def methods_of(self, class_scope: Scope) -> Iterable[Callable]:
        """Iterate methods (callables) declared directly inside ``class_scope``."""
        for c in self.callables():
            if c.parent == class_scope.qualname and c.kind == CallableKind.METHOD:
                yield c

    def superclasses_of(self, class_scope: Scope) -> list[str]:
        """Extract parent-class names declared on ``class_scope``.

        Delegates to ``Language.extract_superclasses`` for the class's
        grammar. Returns an empty list for grammars without inheritance
        (Go, Rust, C, Julia) or class nodes without parents.
        """
        language_id = self._language_by_path.get(str(class_scope.path))
        if language_id is None:
            return []
        lang = LANGUAGE_BY_ID.get(language_id)
        if lang is None:
            return []
        key = (str(class_scope.path), class_scope.qualname)
        node = self._scope_node_by_key.get(key)
        if node is None:
            return []
        for p in self._parses:
            if str(p.path) == str(class_scope.path):
                return lang.extract_superclasses(node, p.content)
        return []

    def weighted_methods(self, class_scope: Scope) -> int:
        """WMC — sum of cyclomatic complexity over the class's methods (CK 1994)."""
        total = 0
        for m in self.methods_of(class_scope):
            total += self.cyclomatic(m)
        return total

    def coupling(self, class_scope: Scope, known_classes: frozenset[str]) -> int:
        """CBO — distinct outbound class references from a class body (CK 1994).

        Walks the class body collecting PascalCase identifier-like
        tokens, intersects with ``known_classes`` (the set of class
        names visible in the corpus), adds declared superclasses that
        are known, excludes self.
        """
        language_id = self._language_by_path.get(str(class_scope.path))
        if language_id is None:
            return 0
        lang = LANGUAGE_BY_ID.get(language_id)
        if lang is None:
            return 0
        key = (str(class_scope.path), class_scope.qualname)
        node = self._scope_node_by_key.get(key)
        if node is None:
            return 0
        content = b""
        for p in self._parses:
            if str(p.path) == str(class_scope.path):
                content = p.content
                break
        ident_types = lang.identifiers()
        refs: set[str] = set()
        stack = [node]
        while stack:
            cur = stack.pop()
            if cur is not node and cur.type in lang.classes():
                # Don't descend into nested classes — they get their own metric.
                continue
            if cur.type in ident_types:
                text = content[cur.start_byte:cur.end_byte].decode("utf-8", errors="replace")
                if text and text[0].isupper():
                    refs.add(text)
            for child in reversed(cur.children):
                stack.append(child)
        refs &= known_classes
        for sc in lang.extract_superclasses(node, content):
            if sc in known_classes:
                refs.add(sc)
        simple = class_scope.qualname.split(".")[-1]
        refs.discard(simple)
        return len(refs)

    def inheritance_depth(
        self, class_scope: Scope, parent_map: dict[str, list[str]], known: frozenset[str],
    ) -> int:
        """DIT — depth of inheritance tree from this class (CK 1994).

        ``parent_map`` is a precomputed mapping of simple class name →
        list of declared parent names (caller builds it once across the
        corpus). ``known`` is the set of class names present in the
        corpus; only known parents contribute to depth (unknown
        parents are external references). Cycle-safe.
        """
        visited: set[str] = set()
        max_depth = 0

        def walk(current: str, depth: int) -> None:
            nonlocal max_depth
            if current in visited:
                return
            visited.add(current)
            if depth > max_depth:
                max_depth = depth
            for parent in parent_map.get(current, []):
                if parent in known:
                    walk(parent, depth + 1)

        walk(class_scope.qualname.split(".")[-1], 0)
        return max_depth

    def subclasses_count(
        self, class_scope: Scope, children_map: dict[str, list[str]],
    ) -> int:
        """NOC — direct subclass count (CK 1994).

        ``children_map`` maps simple class name → list of simple names
        of classes that declare it as a parent. Caller builds it once.
        """
        return len(children_map.get(class_scope.qualname.split(".")[-1], []))

    # ---- cross-cutting compute methods -------------------------------

    def hotspots(
        self,
        root: Any,
        *,
        since: str | None = "14 days ago",
        until: str | None = None,
        min_commits: int = 2,
        hotspot_percentile: float = 0.75,
    ):
        """Per-file growth-weighted complexity hotspots (Tornhill 2015).

        Aggregates cyclomatic complexity from this view's callables
        bucketed by file, joins with git numstat over ``since``..``until``
        (LOC delta = insertions − deletions), and classifies into
        quadrants by 75th-percentile cutoffs on both axes. Score is
        ``sum_ccx × max(0, loc_delta)``; files that shrank in the
        window keep their raw delta for display but score as zero.

        Returns a ``HotspotsComputeResult`` carrying rich
        ``FileHotspot`` records sorted worst-first plus diagnostic
        metadata. The rule layer (``run_churn_weighted``) threshold-
        checks the records into ``Slop`` findings.
        """
        from pathlib import Path as _Path

        from slop.structure._hotspots import compute_hotspots

        return compute_hotspots(
            self, _Path(root),
            since=since, until=until,
            min_commits=min_commits,
            hotspot_percentile=hotspot_percentile,
        )

    def orphans(
        self,
        root: Any,
        *,
        min_name_length: int = 4,
        max_refs: int = 0,
    ):
        """Enumerate definitions with zero detected external references.

        Iterates top-level callables and named class-like scopes from
        this view, then uses ripgrep (``grep_kernel``) to count word-
        boundary references in OTHER files. Methods and nested
        functions are skipped — name-based reference counting on
        them is too noisy (matches every property access on every
        object).

        Confidence is heuristic: short names and common verbs
        (``run`` / ``main`` / ``get``) get downgraded because they
        collide with unrelated identifiers; Python / JavaScript / Ruby
        lose a step because reflection and dynamic dispatch can't be
        detected statically.

        Returns an ``OrphansComputeResult``. The rule layer
        (``run_orphans``) applies a ``min_confidence`` filter.
        """
        from pathlib import Path as _Path

        from slop.structure._orphans import compute_orphans

        return compute_orphans(
            self, _Path(root),
            min_name_length=min_name_length, max_refs=max_refs,
        )

    def imports(self):
        """Raw import / include / require edges per file.

        One ``Import`` record per ``@module`` capture across every
        parsed file. Resolution to file→file edges is a separate step
        (see ``dependency_graph``); this method returns the unresolved
        edges so language-aware consumers can post-process the raw
        module strings.

        Returns a ``list[Import]``. Files whose grammar declares no
        ``import_queries()`` contribute nothing.
        """
        from slop.structure._imports import extract_imports

        return extract_imports(self._parses)

    def packages(self, root: Any):
        """Per-package architecture metrics (Martin 1994 D' = |A + I - 1|).

        Groups files into packages via each grammar's
        ``Language.resolve_packages``, counts abstract/concrete scopes
        via ``Language.is_abstract_scope``, and aggregates the
        file-level dependency graph to package-level Ca/Ce. Returns
        one ``PackageMetrics`` per resolved package, zone-classified
        per legacy thresholds.

        Packages whose grammar declares no abstractness signal end up
        in the ``unknown`` zone — this is intentional. The legacy
        kernel rounded the same situation to "Zone of Pain" (Na = 0,
        Nc = N), which is a false signal: there's no abstractness
        evidence either way. ``unknown`` is the honest classification.
        """
        from pathlib import Path as _Path

        from slop.structure._packages import compute_packages

        return compute_packages(self, _Path(root))

    def hidden_mutators(self, *, require_type_annotation: bool = True):
        """Functions that silently mutate their parameters in place.

        Iterates callables and asks each grammar to report mutation
        events on its callables' bodies. Returns ``list[HiddenMutator]``
        with per-event detail; the rule layer threshold-checks the
        mutation count.
        """
        from slop.structure._hidden_mutators import compute_hidden_mutators

        return compute_hidden_mutators(
            self, require_type_annotation=require_type_annotation,
        )

    def sentinel_parameters(self, *, require_str_annotation: bool = True):
        """Stringly-typed parameter candidates across the corpus.

        Iterates callables, extracts parameters via each grammar's
        ``stringly_typed_params`` hook, filters to the universal
        sentinel-name list, and enriches each candidate with the
        distinct string literals observed at call sites (substrate-
        native — no external grep).

        Returns ``list[SentinelParameter]``. The rule layer applies
        ``max_cardinality`` thresholds.
        """
        from slop.structure._sentinels import compute_sentinels

        return compute_sentinels(
            self, require_str_annotation=require_str_annotation,
        )

    def type_annotations(self):
        """Tree-sitter-extracted type annotations across the corpus.

        Yields one ``TypeAnnotation`` record per ``@annotation`` capture
        from each grammar's ``type_annotation_queries``. The
        ``is_escape`` field is set by the grammar's
        ``is_escape_hatch_text`` predicate.

        Supported grammars: Python, TypeScript, Go, Rust, Java, C#,
        Julia. JavaScript / C / C++ / Ruby return no annotations
        (JSDoc isn't in the AST; C/C++ encode types in declarations
        not annotation nodes; Ruby is dynamically typed).
        """
        from slop.structure._annotations import extract_annotations

        return extract_annotations(self)

    def callees_of(self, callable_record):
        """Non-trivial callee names extracted from one callable's body.

        Walks the callable's AST body looking for call-expression
        nodes (per the grammar's ``call_node_types``), pulls the
        callee name via ``extract_callee_name``, and filters out
        per-grammar trivial callees plus universal noise (length < 3,
        dunder names). Returns a frozenset.
        """
        from slop.structure._redundancy import callees_of

        return callees_of(self, callable_record)

    def redundant_siblings(
        self, *, min_shared: int = 3, min_score: float = 0.5,
    ):
        """Pairs of sibling top-level callables with overlapping callee sets.

        Refactoring signal: when two peer functions both call the same
        helpers, either a shared helper should encapsulate the common
        calls, or one is a partial copy of the other. Walks callables
        per file, computes pairwise callee-set intersections, and
        emits a ``RedundancyPair`` per pair whose ``|shared| >= min_shared``
        AND whose ``score >= min_score``.
        """
        from slop.structure._redundancy import compute_redundancy

        return compute_redundancy(
            self, min_shared=min_shared, min_score=min_score,
        )

    def clones(self, *, min_leaf_nodes: int = 10):
        """Type-2 clone clusters — callables sharing an AST leaf-type fingerprint.

        Identifier names and literal values are discarded; only the
        structural shape of the body subtree is fingerprinted. The
        body subtree is found via each grammar's ``block_types()``
        vocabulary. Functions whose leaf count is below
        ``min_leaf_nodes`` are excluded — trivial bodies (``pass``,
        ``return``) produce noise.

        Returns a ``CloneReport`` carrying clone clusters (size >= 2),
        the total number of callables analyzed, and the corpus-level
        clone fraction (cloned callables / total callables).
        """
        from slop.structure._clones import compute_clones

        return compute_clones(self, min_leaf_nodes=min_leaf_nodes)

    def dependency_cycles(self) -> list[list[str]]:
        """Import cycles in the corpus (Tarjan 1972 SCC on the resolved graph).

        Each returned entry is a strongly connected component of more
        than one file, sorted by absolute path. Self-loops are dropped
        at the resolver layer. The Acyclic Dependencies Principle
        (Lakos 1996; Martin 2002 ch. 20) holds that any cycle prevents
        independent reasoning, testing, or extraction of any module in
        the loop.
        """
        from slop.structure._imports import detect_cycles

        return detect_cycles(self.dependency_graph())

    def dependency_graph(self):
        """File→file import graph with raw modules resolved against the corpus.

        Builds a flat module-name index from every parsed file (dotted,
        slashed, stem, ``__init__.py`` package forms), then asks each
        grammar to resolve its own raw module strings via
        ``Language.resolve_module``. Unresolved imports are dropped.

        Returns a ``DependencyGraph`` with ``efferent`` (outbound) and
        ``afferent`` (inbound) adjacency maps.
        """
        from slop.structure._imports import build_dependency_graph, extract_imports

        return build_dependency_graph(self._parses, extract_imports(self._parses))

    # ---- slicing -----------------------------------------------------

    def under(self, *, path: str | None = None) -> Structure:
        new_filters = list(self._filters)
        if path is not None:
            path_prefix = path
            new_filters.append(lambda rec: str(rec.path).startswith(path_prefix))
        return Structure(self._parses, filters=tuple(new_filters))

    def where(
        self,
        *,
        language: str | None = None,
        kind: ScopeKind | CallableKind | None = None,
    ) -> Structure:
        new_filters = list(self._filters)
        if language is not None:
            lang = language
            lang_map = self._language_by_path
            new_filters.append(lambda rec: lang_map.get(str(rec.path)) == lang)
        if kind is not None:
            k = kind
            new_filters.append(lambda rec: getattr(rec, "kind", None) == k)
        return Structure(self._parses, filters=tuple(new_filters))


def _resolve_body(node: Any, unwrap: frozenset[str]) -> Any:
    """Descend through wrapper nodes (e.g. C++ ``template_declaration``)
    to the actual definition's body field. Falls back to the node itself
    when no body field exists.
    """
    current = node
    # Unwrap up to a small fixed depth — guards against malformed ASTs.
    for _ in range(4):
        if current.type not in unwrap:
            break
        # Find the wrapped definition among the children.
        next_node = None
        for child in current.children:
            if child.type != current.type and child.type not in ("(", ")", "<", ">", ","):
                next_node = child
                break
        if next_node is None:
            break
        current = next_node
    body = current.child_by_field_name("body")
    return body if body is not None else current


def _count_decisions(
    node: Any,
    decision_nodes: frozenset[str],
    bool_op_node: str | None,
    bool_op_operators: frozenset[str] | None,
    nested_callables: frozenset[str],
    content: bytes,
) -> int:
    """Recursively count cyclomatic decision points under ``node``.

    ``nested_callables`` is the per-language set of node types that
    define a new callable scope (i.e. ``Language.callable()``). The
    walk does not descend into nested callables — each callable's
    metric is body-local. Honours per-language short-circuit operator
    filtering: when ``bool_op_operators`` is None, every
    ``bool_op_node`` instance counts (Python's dedicated
    ``boolean_operator``); when non-None, only nodes whose operator
    text is in the set count (C-family ``binary_expression`` with
    ``&&``/``||``/``??``).
    """
    count = 0
    stack = [node]
    while stack:
        cur = stack.pop()
        ctype = cur.type
        if ctype in nested_callables and cur is not node:
            continue
        if ctype in decision_nodes:
            count += 1
        if bool_op_node is not None and ctype == bool_op_node:
            if bool_op_operators is None or _bool_op_matches(cur, bool_op_operators, content):
                count += 1
        stack.extend(reversed(cur.children))
    return count


def _bool_op_matches(
    node: Any,
    operators: frozenset[str],
    content: bytes,
) -> bool:
    """True if ``node``'s operator text is in ``operators``.

    Tree-sitter grammars expose the operator in three different shapes:
      1. As an ``operator`` field on the binary node (JS/TS/Go/Java/C#).
      2. As a named child node of type ``operator`` (Julia, Ruby).
      3. As an unnamed punctuation token between the operands (some
         older grammars).
    All three are handled.
    """
    op_text = _bool_op_text(node, content)
    return op_text in operators if op_text else False


def _bool_op_text(node: Any, content: bytes) -> str:
    """Extract the operator text from a boolean/binary operator node.

    Tree-sitter grammars expose the operator in four shapes:
      1. As an ``operator`` field on the binary node (JS/TS/Go/Java/C#/C/C++).
      2. As a named child node of type ``operator`` (Julia, Ruby).
      3. As a child whose type name IS the operator keyword (Python:
         ``and`` / ``or`` / ``not``).
      4. As an unnamed punctuation token between operands.

    Returns the operator text or ``""`` if no operator child can be found.
    """
    op_node = node.child_by_field_name("operator")
    if op_node is not None:
        return content[op_node.start_byte:op_node.end_byte].decode("utf-8", errors="replace")
    for child in node.children:
        if child.type == "operator":
            return content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
        if child.type in ("and", "or", "not"):
            return child.type
        if not child.is_named:
            text = content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            if text in ("&&", "||", "??", "and", "or"):
                return text
    return ""


@dataclass(frozen=True)
class _NPathVocab:
    """Per-language vocabulary bundle for the combinatorial walker.

    Pulled together from the ``Language`` class once per
    ``Structure.combinatorial`` call to avoid threading 13 separate
    arguments through the recursive helpers below.
    """
    if_nodes: frozenset[str]
    elif_nodes: frozenset[str]
    else_nodes: frozenset[str]
    loop_nodes: frozenset[str]
    switch_nodes: frozenset[str]
    case_nodes: frozenset[str]
    try_nodes: frozenset[str]
    catch_nodes: frozenset[str]
    body_field: str
    block_types: frozenset[str]
    switch_body_types: frozenset[str]
    body_skip_types: frozenset[str]
    bare_else_keyword: str | None
    nested_callables: frozenset[str]
    definition_unwrap_types: frozenset[str]

    @classmethod
    def for_language(cls, lang: Any) -> _NPathVocab:
        return cls(
            if_nodes=lang.if_nodes(),
            elif_nodes=lang.elif_nodes(),
            else_nodes=lang.else_nodes(),
            loop_nodes=lang.loop_nodes(),
            switch_nodes=lang.switch_nodes(),
            case_nodes=lang.case_nodes(),
            try_nodes=lang.try_nodes(),
            catch_nodes=lang.catch_nodes(),
            body_field=lang.body_field(),
            block_types=lang.block_types(),
            switch_body_types=lang.switch_body_types(),
            body_skip_types=lang.body_skip_types(),
            bare_else_keyword=lang.bare_else_keyword(),
            nested_callables=lang.callable(),
            definition_unwrap_types=lang.definition_unwrap_types(),
        )


def _unwrap_definition(node: Any, unwrap: frozenset[str]) -> Any:
    """Descend through wrapper nodes (e.g. C++ ``template_declaration``)
    to the actual definition. Fixed-depth guard against malformed ASTs.
    """
    current = node
    for _ in range(4):
        if current.type not in unwrap:
            break
        next_node = None
        for child in current.children:
            if child.type != current.type and child.type not in ("(", ")", "<", ">", ","):
                next_node = child
                break
        if next_node is None:
            break
        current = next_node
    return current


def _npath_walk(callable_node: Any, vocab: _NPathVocab) -> int:
    """Compute NPath of a callable definition's body.

    For grammars with a body field (most), descends into the field
    and walks it as a sequence of statements. For flat-body grammars
    (Julia, Ruby), walks the callable's direct children filtering by
    ``body_skip_types``.
    """
    if vocab.body_field:
        body = callable_node.child_by_field_name(vocab.body_field)
        if body is None:
            return 1
        return _npath_of_block(body, vocab)
    return _npath_of_flat_body(callable_node, vocab)


def _npath_of_block(node: Any, vocab: _NPathVocab) -> int:
    """NP of a sequence of statements.

    If ``node`` is itself a block wrapper, multiplies its children's
    NPs; otherwise treats ``node`` as a single statement.
    """
    if node is None:
        return 1
    if node.type in vocab.block_types:
        result = 1
        for child in node.children:
            result *= _npath_of_node(child, vocab)
        return result
    return _npath_of_node(node, vocab)


def _npath_of_flat_body(node: Any, vocab: _NPathVocab) -> int:
    """NP of a flat-body construct (Julia, Ruby).

    Walks direct children, skipping structural-keyword node types
    enumerated in ``body_skip_types``, and multiplies non-trivial NPs.
    """
    result = 1
    for child in node.children:
        if child.type in vocab.body_skip_types:
            continue
        cn = _npath_of_node(child, vocab)
        if cn > 1:
            result *= cn
    return result


def _npath_of_node(node: Any, vocab: _NPathVocab) -> int:
    """Dispatch NP contribution of a single AST node by its structural role."""
    ntype = node.type

    if ntype in vocab.if_nodes or ntype in vocab.elif_nodes:
        return _npath_of_if(node, vocab)

    if ntype in vocab.loop_nodes:
        if vocab.body_field:
            body = node.child_by_field_name(vocab.body_field)
            return _npath_of_block(body, vocab) + 1
        return _npath_of_flat_body(node, vocab) + 1

    if ntype in vocab.switch_nodes:
        return _npath_of_switch(node, vocab)

    if ntype in vocab.try_nodes:
        return _npath_of_try(node, vocab)

    # Nested callable: each has its own metric — do not descend.
    if ntype in vocab.nested_callables:
        return 1

    # Generic compound: walk through, multiplying non-trivial children.
    result = 1
    for child in node.children:
        cn = _npath_of_node(child, vocab)
        if cn > 1:
            result *= cn
    return result


def _npath_of_switch(node: Any, vocab: _NPathVocab) -> int:
    """NP of a switch/match — sum of case NPs (>= 1).

    Some grammars (Java ``switch_block`` / C# ``switch_body`` / C/C++
    ``compound_statement``) wrap cases inside an intermediate block;
    ``switch_body_types`` tells the walker to recurse through them.
    """
    def iter_cases(parent: Any) -> Iterable[Any]:
        for child in parent.children:
            if child.type in vocab.case_nodes:
                yield child
            elif child.type in vocab.switch_body_types:
                yield from iter_cases(child)

    total = 0
    for case_child in iter_cases(node):
        case_np = 1
        for cc in case_child.children:
            if cc.type in vocab.block_types:
                case_np = _npath_of_block(cc, vocab)
        total += case_np
    return max(total, 1)


def _npath_of_try(node: Any, vocab: _NPathVocab) -> int:
    """NP of a try/catch — try-body NP + sum of catch-body NPs."""
    try_body_np = 1
    handler_sum = 0
    for child in node.children:
        if child.type in vocab.block_types:
            try_body_np = _npath_of_block(child, vocab)
        elif child.type in vocab.catch_nodes:
            if vocab.body_field:
                catch_body = child.child_by_field_name(vocab.body_field)
                handler_sum += _npath_of_block(catch_body, vocab) if catch_body is not None else 1
            else:
                handler_sum += _npath_of_flat_body(child, vocab)
    if handler_sum == 0:
        return try_body_np
    return try_body_np + handler_sum


def _npath_of_if(node: Any, vocab: _NPathVocab) -> int:
    """NP of an if/elif/else chain — sum of branch NPs.

    Adds +1 for an implicit fall-through path when no terminal
    ``else`` is present. Handles three else shapes:
      - else-clause wrapper (Python, Ruby, Java, C, C++, Go, ...)
      - bare ``else`` keyword followed by a block (C#)
      - C-style ``else { if … }`` nested chains
    """
    then_np = 1
    consequence = node.child_by_field_name("consequence")
    if consequence is not None and consequence.type in vocab.block_types:
        then_np = _npath_of_block(consequence, vocab)
    else:
        for child in node.children:
            if child.type in vocab.block_types:
                then_np = _npath_of_block(child, vocab)
                break

    alt_nps: list[int] = []
    has_terminal = False

    for child in node.children:
        if child.type in vocab.elif_nodes:
            elif_body_np = 1
            for ec in child.children:
                if ec.type in vocab.block_types:
                    elif_body_np = _npath_of_block(ec, vocab)
            alt_nps.append(elif_body_np)
        elif child.type in vocab.else_nodes:
            has_terminal = True
            else_added = False
            for ec in child.children:
                if ec.type in vocab.block_types:
                    alt_nps.append(_npath_of_block(ec, vocab))
                    else_added = True
                elif ec.type in vocab.if_nodes:
                    # C-style else-if chain
                    alt_nps.append(_npath_of_if(ec, vocab))
                    else_added = True
            if not else_added and not vocab.body_field:
                # Flat-body langs (Julia): else_clause has no block
                # wrapper; treat as +1 path. Nested control flow
                # inside the else is not deeply analysed (documented
                # limitation, inherited from the legacy kernel).
                alt_nps.append(1)

    # Bare-keyword else (C#): "else" keyword child followed by a block
    # or nested if_statement as the next sibling.
    if vocab.bare_else_keyword and not has_terminal:
        children = list(node.children)
        for i, child in enumerate(children):
            if child.type == vocab.bare_else_keyword and i + 1 < len(children):
                nxt = children[i + 1]
                has_terminal = True
                if nxt.type in vocab.block_types:
                    alt_nps.append(_npath_of_block(nxt, vocab))
                elif nxt.type in vocab.if_nodes:
                    alt_nps.append(_npath_of_if(nxt, vocab))

    if not has_terminal:
        return then_np + sum(alt_nps) + 1
    return then_np + sum(alt_nps)


def _cognitive_walk(
    root: Any,
    decision_nodes: frozenset[str],
    nesting_nodes: frozenset[str],
    compensating: frozenset[str],
    bool_op_node: str | None,
    bool_op_operators: frozenset[str] | None,
    nested_callables: frozenset[str],
    content: bytes,
) -> int:
    """Walk ``root`` accumulating Cognitive Complexity (Campbell 2018).

    Iterative stack walk where each entry carries the current nesting
    depth. Each decision node contributes ``1 + depth``; compensating
    decisions contribute ``1 + max(0, depth - 1)``. Short-circuit
    operators count +1 unless they're continuing a same-operator chain
    with their syntactic parent (tree-sitter ``node.parent``).
    """
    cog = 0
    stack: list[tuple[Any, int]] = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        ctype = node.type

        # Skip nested callables; each gets its own metric.
        if ctype in nested_callables and node is not root:
            continue

        # Decision contribution.
        if ctype in decision_nodes:
            if ctype in compensating:
                cog += 1 + max(0, depth - 1)
            else:
                cog += 1 + depth

        # Boolean operator with sequence collapsing.
        if bool_op_node is not None and ctype == bool_op_node:
            op_text = _bool_op_text(node, content)
            counts = (bool_op_operators is None) or (op_text in bool_op_operators)
            if counts:
                parent = node.parent
                in_continuing_sequence = False
                if parent is not None and parent.type == bool_op_node:
                    parent_op = _bool_op_text(parent, content)
                    parent_counts = (
                        bool_op_operators is None or parent_op in bool_op_operators
                    )
                    if parent_counts and parent_op == op_text:
                        in_continuing_sequence = True
                if not in_continuing_sequence:
                    cog += 1

        # Children inherit incremented depth if this node is a nester.
        new_depth = depth + 1 if ctype in nesting_nodes else depth
        for child in reversed(node.children):
            stack.append((child, new_depth))

    return cog
