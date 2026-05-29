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

from typing import Any, Callable as TypingCallable, Iterable, Sequence

from slop.language.grammars import LANGUAGE_BY_ID
from slop.structure import complexity
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

    def _lang_for(self, path: Any) -> Any | None:
        """Resolve the ``Language`` object for a source path, or None."""
        language_id = self._language_by_path.get(str(path))
        if language_id is None:
            return None
        return LANGUAGE_BY_ID.get(language_id)

    # ---- compute methods (views delegate to algorithm modules) -------

    def cyclomatic(self, c: Callable) -> int:
        """McCabe cyclomatic complexity for one callable (McCabe 1976).

        Resolves the callable's AST node, content, and ``Language`` and
        delegates the walk to ``complexity.cyclomatic``. Callables with
        no parsed node, content, or resolvable language score CCX=1.
        """
        key = (str(c.path), c.qualname)
        node = self._node_by_key.get(key)
        content = self._content_by_key.get(key)
        if node is None or content is None:
            return 1
        lang = self._lang_for(c.path)
        if lang is None:
            return 1
        return complexity.cyclomatic(node, content, lang)

    def combinatorial(self, c: Callable) -> int:
        """NPath — acyclic execution-path count for one callable (Nejmeh 1988).

        Resolves the callable's AST node and ``Language`` and delegates
        the multiplicative path-count walk to ``complexity.combinatorial``.
        Callables with no parsed node or resolvable language score NP=1.
        """
        key = (str(c.path), c.qualname)
        node = self._node_by_key.get(key)
        if node is None:
            return 1
        lang = self._lang_for(c.path)
        if lang is None:
            return 1
        return complexity.combinatorial(node, lang)

    def cognitive(self, c: Callable) -> int:
        """Cognitive Complexity for one callable (Campbell 2018).

        Resolves the callable's AST node, content, and ``Language`` and
        delegates the nesting-weighted walk to ``complexity.cognitive``.
        Callables with no parsed node, content, or resolvable language
        score CogC=0.
        """
        key = (str(c.path), c.qualname)
        node = self._node_by_key.get(key)
        content = self._content_by_key.get(key)
        if node is None or content is None:
            return 0
        lang = self._lang_for(c.path)
        if lang is None:
            return 0
        return complexity.cognitive(node, content, lang)

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

    def class_vocabularies(self) -> dict[str, set[str]]:
        """Return ``{class_qualname: set of method-name tokens}``.

        For each class-like scope, collect the snake/Camel-split lowercased
        token set of every method whose ``parent`` qualname matches the
        scope. Consumed by the class-ownership packet filter — a packet
        whose tokens are entirely covered by some class's vocabulary is
        a *conventional* packet (the class is the abstraction the
        vocabulary expresses) rather than a *pathological* one (drift).
        """
        from slop.lexicon.view import Lexicon

        out: dict[str, set[str]] = {}
        class_qualnames = {s.qualname for s in self.classes()}
        for c in self.callables():
            if c.parent not in class_qualnames:
                continue
            simple = c.qualname.rsplit(".", 1)[-1]
            if not simple or simple.startswith("<"):
                continue
            bag = out.setdefault(c.parent, set())
            for t in Lexicon.split_tokens(simple):
                bag.add(t.lower())
        return out

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

    def weighted_cognitive(self, class_scope: Scope) -> int:
        """Class-scope sum of cognitive complexity (CK-style aggregation, Campbell 2018)."""
        total = 0
        for m in self.methods_of(class_scope):
            total += self.cognitive(m)
        return total

    def weighted_combinatorial(self, class_scope: Scope) -> int:
        """Class-scope sum of NPath (CK-style aggregation, Nejmeh 1988)."""
        total = 0
        for m in self.methods_of(class_scope):
            total += self.combinatorial(m)
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

        Returns a ``hotspots.ComputeResult`` carrying rich
        ``FileHotspot`` records sorted worst-first plus diagnostic
        metadata. The rule layer (``run_churn_weighted``) threshold-
        checks the records into ``Slop`` findings.
        """
        from pathlib import Path as _Path

        from slop.structure import hotspots

        return hotspots.compute(
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

        Returns an ``orphans.ComputeResult``. The rule layer
        (``run_orphans``) applies a ``min_confidence`` filter.
        """
        from pathlib import Path as _Path

        from slop.structure import orphans

        return orphans.compute(
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
        from slop.structure.imports import extract_imports

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

        from slop.structure.packages import compute_packages

        return compute_packages(self, _Path(root))

    def hidden_mutators(self, *, require_type_annotation: bool = True):
        """Functions that silently mutate their parameters in place.

        Iterates callables and asks each grammar to report mutation
        events on its callables' bodies. Returns ``list[HiddenMutator]``
        with per-event detail; the rule layer threshold-checks the
        mutation count.
        """
        from slop.structure import hidden_mutators

        return hidden_mutators.compute(
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
        from slop.structure.sentinels import compute_sentinels

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
        from slop.structure.annotations import extract_annotations

        return extract_annotations(self)

    def callees_of(self, callable_record):
        """Non-trivial callee names extracted from one callable's body.

        Walks the callable's AST body looking for call-expression
        nodes (per the grammar's ``call_node_types``), pulls the
        callee name via ``extract_callee_name``, and filters out
        per-grammar trivial callees plus universal noise (length < 3,
        dunder names). Returns a frozenset.
        """
        from slop.structure.redundancy import callees_of

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
        from slop.structure.redundancy import compute_redundancy

        return compute_redundancy(
            self, min_shared=min_shared, min_score=min_score,
        )

    def redundancy_clusters(
        self, *, min_shared: int = 3, min_score: float = 0.5,
    ) -> dict[str, list[frozenset[str]]]:
        """Per-file disjoint clusters of redundant sibling functions.

        Groups ``redundant_siblings`` pairs into connected components
        (union-find) per file. Each cluster is a set of function names
        that transitively share callees — a cohesive call-island. A file
        with **two or more disjoint clusters** holds multiple independent
        cohesive units: the coordinator-over-islands (grab-bag) topology
        that the confusion rule consumes.

        Returns ``{file: [frozenset(member_names), ...]}`` — only files
        with at least one cluster appear.
        """
        pairs = self.redundant_siblings(min_shared=min_shared, min_score=min_score)
        by_file: dict[str, list] = {}
        for p in pairs:
            by_file.setdefault(p.file, []).append(p)

        clustered: dict[str, list[frozenset[str]]] = {}
        for file, file_pairs in by_file.items():
            parent: dict[str, str] = {}

            def find(x: str, parent=parent) -> str:
                parent.setdefault(x, x)
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x

            for p in file_pairs:
                ra, rb = find(p.fn_a), find(p.fn_b)
                if ra != rb:
                    parent[ra] = rb

            groups: dict[str, set[str]] = {}
            for p in file_pairs:
                root = find(p.fn_a)
                members = groups.setdefault(root, set())
                members.add(p.fn_a)
                members.add(p.fn_b)
            clustered[file] = [frozenset(m) for m in groups.values()]
        return clustered

    def intra_file_call_components(self) -> dict[str, list[frozenset[str]]]:
        """Connected components of each file's intra-file call graph.

        Nodes are a file's callables (by simple name); an undirected edge
        joins caller and callee when both are defined in that file
        (name-matched). Returns ``{file: [frozenset(names), ...]}`` with
        every callable in exactly one component (isolated functions are
        singletons).

        This is the should-split discriminator the confusion rule layers
        on top of ``redundancy_clusters``: if a file's redundancy islands
        all fall in ONE component, a coordinator bridges them — a cohesive
        pipeline, leave it. If the islands span TWO OR MORE components,
        nothing connects them — a genuine disconnected grab-bag. The
        coordinator that defeats plain island-detection is exactly what
        makes the components merge, so it is a feature here, not a bug.
        """
        by_file: dict[str, list] = {}
        for c in self.callables():
            by_file.setdefault(str(c.path), []).append(c)

        out: dict[str, list[frozenset[str]]] = {}
        for file, callables in by_file.items():
            names = {c.qualname.rsplit(".", 1)[-1] for c in callables}
            parent: dict[str, str] = {n: n for n in names}

            def find(x: str, parent=parent) -> str:
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x

            for c in callables:
                caller = c.qualname.rsplit(".", 1)[-1]
                for callee in self.callees_of(c):
                    if callee in names and callee != caller:
                        parent[find(callee)] = find(caller)

            groups: dict[str, set[str]] = {}
            for n in names:
                groups.setdefault(find(n), set()).add(n)
            out[file] = [frozenset(g) for g in groups.values()]
        return out

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
        from slop.structure.clones import compute_clones

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
        from slop.structure.imports import detect_cycles

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
        from slop.structure.imports import build_dependency_graph, extract_imports

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
