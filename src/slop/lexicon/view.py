"""Lexicon view — the substrate lexical rules consume.

A ``Lexicon`` is a windowed view over the identifier-token bag
extracted from the parsed corpus. Lexical rules (sprawl, slackers,
imposters, confusion, hammers, stutter, cowards, tautology, verbosity)
depend on this surface; they do not see the AST tree shape.

This class is DISTINCT from the legacy ``_lexical/_words.py:Lexicon``,
which is a flat-bag-of-Lexeme structure with no scope axis. The legacy
Lexicon serves group-B rules during the migration window and retires
in the deletion sweep (see ``docs/planning/migration.md``).

The view owns metric computations. Rules call methods like
``first_param_clusters()``; AST walking happens inside the view,
hidden behind the compute API. Records remain pure-data identifiers.

Slicing methods (``under``, ``where``, ``walk``) return NEW ``Lexicon``
instances over the same underlying parse data. Cost is O(1); the view
is a filter, not a copy.

See ``docs/planning/codebase.md`` for the locked design.
"""
from __future__ import annotations

from typing import (
    AbstractSet,
    Any,
    Callable as TypingCallable,
    Iterable,
    Mapping,
    Sequence,
)

from slop._lexical._naming import scope_label

from slop.tree.records import Callable, Occurrence, ParseResult


class Lexicon:
    """View over the corpus's identifier-token bag + callable signals.

    Constructed once by ``Tree.scan()``; consumed by lexical rules.
    Immutable by contract: stat queries return new structures; slicing
    returns new ``Lexicon`` instances.
    """

    def __init__(
        self,
        parses: Sequence[ParseResult],
        *,
        filters: Sequence[TypingCallable[[Any], bool]] = (),
    ) -> None:
        self._parses = tuple(parses)
        self._filters = tuple(filters)

        # Per-callable indexes keyed by (path, qualname) — a bare qualname
        # like ``a.f`` collides across same-file-stem corpora; pairing it
        # with the absolute path scopes the lookup to its source file.
        # Records stay pure-data; AST state lives in the view per the
        # views-own-compute principle.
        self._language_by_path: dict[str, str] = {}
        self._callable_by_key: dict[tuple[str, str], Callable] = {}
        self._node_by_key: dict[tuple[str, str], Any] = {}
        self._content_by_path: dict[str, bytes] = {}
        self._parts_by_key: dict[tuple[str, str], tuple[str, ...]] = {}

        for p in parses:
            self._language_by_path[str(p.path)] = p.language
            self._content_by_path[str(p.path)] = p.content
            for c in p.callables:
                key = (str(c.path), c.qualname)
                self._callable_by_key[key] = c
                if c.qualname in p.callable_nodes:
                    self._node_by_key[key] = p.callable_nodes[c.qualname]
                self._parts_by_key[key] = c.path.parts

    # ---- statistical queries (stubbed; land with their first consumer) -----

    def frequencies(self) -> Mapping[str, int]:
        """Token → occurrence-count over this view.

        Lands when sprawl ports (Intent 13).
        """
        raise NotImplementedError

    def modal_tokens(self, *, top: int = 10) -> Sequence[tuple[str, int]]:
        """Top-``top`` tokens by frequency, descending.

        Lands when sprawl ports (Intent 13).
        """
        raise NotImplementedError

    def alphabet(self) -> AbstractSet[str]:
        """The distinct tokens observed in this view."""
        raise NotImplementedError

    def coverage(self, vocabulary: AbstractSet[str]) -> float:
        """Fraction of this view's tokens that appear in ``vocabulary``."""
        raise NotImplementedError

    def overlap(self, other: Lexicon) -> float:
        """Jaccard-style overlap between this view's alphabet and ``other``'s."""
        raise NotImplementedError

    # ---- per-callable compute methods --------------------------------------

    def first_param_clusters(
        self,
        *,
        min_cluster: int = 3,
        exempt_names: frozenset[str] = frozenset({"self", "cls"}),
        root: Any = None,
    ) -> list[Any]:
        """Group callables by their first parameter; emit clusters at
        the narrowest scope where they cohere.

        Returns ``FirstParameterCluster`` instances (imported from the
        legacy kernel during the migration window — the dataclass is
        pure-data and is renamed in the deletion sweep). Hierarchical
        traversal: a callable appears in at most one cluster, claimed
        at the deepest scope where the cluster reaches ``min_cluster``.

        ``root`` is the codebase root used to derive relative paths for
        the path-parts decomposition that drives scope claiming. If
        None, falls back to the longest common prefix across observed
        callable paths.
        """
        # Import legacy FirstParameterCluster + helpers. Build-beside:
        # the legacy module is unchanged; we only read it.
        from slop._lexical.imposters import FirstParameterCluster, _classify_cluster

        # Build _FuncEntry-equivalent records for the clustering walk.
        # We use lightweight tuples instead of importing _FuncEntry (private).
        from pathlib import Path

        if root is None:
            # Best-effort: derive from common prefix.
            paths = [c.path for c in self._callable_by_key.values()]
            if paths:
                try:
                    root = Path(_common_prefix(paths))
                except Exception:
                    root = paths[0].parent
            else:
                return []
        root_path = Path(root)

        # entries: list of (name, file_rel, line, parts, param_name, param_type)
        from slop.tree.records import CallableKind  # local import to avoid cycle
        entries: list[tuple[str, str, int, tuple[str, ...], str | None, str | None]] = []
        for c in self._callable_by_key.values():
            if not all(f(c) for f in self._filters):
                continue
            # Lambdas are excluded from first-parameter clustering. Their
            # first parameter is typically a closure variable, not a
            # receiver candidate; the legacy ``enumerate_functions``
            # walker excluded lambdas for the same reason.
            if c.kind == CallableKind.LAMBDA:
                continue
            # Skip "self"/"cls" first parameters for methods
            first_param = None
            first_type: str | None = None
            for p in c.parameters:
                if p.name in exempt_names:
                    continue
                first_param = p.name
                first_type = p.annotation
                break
            try:
                rel = c.path.relative_to(root_path)
                parts = rel.parts
                file_rel = str(rel)
            except ValueError:
                parts = c.path.parts
                file_rel = str(c.path)
            # Use simple base-name (without qualname prefix) for member naming —
            # matches the legacy ``ctx.name`` convention.
            simple_name = c.qualname.split(".")[-1]
            entries.append((simple_name, file_rel, c.line, parts, first_param, first_type))

        # Hierarchical clustering: mirror the legacy
        # ``_recursive_first_param_findings`` algorithm.
        by_prefix: dict[tuple[str, ...], list[tuple]] = {(): list(entries)}
        for e in entries:
            parts = e[3]
            for depth in range(1, len(parts) + 1):
                by_prefix.setdefault(parts[:depth], []).append(e)

        prefixes = sorted(by_prefix.keys(), key=lambda p: -len(p))
        findings: list[Any] = []
        claimed: set[tuple[str, str]] = set()

        for prefix in prefixes:
            scope_funcs = [
                e for e in by_prefix[prefix] if (e[1], e[0]) not in claimed
            ]
            if len(scope_funcs) < min_cluster:
                continue

            is_root = not prefix
            is_file = bool(prefix) and "." in prefix[-1]

            by_param: dict[str, list[tuple]] = {}
            for e in scope_funcs:
                pname = e[4]
                if pname is None or len(pname) < 2:
                    continue
                by_param.setdefault(pname, []).append(e)

            for pname, members in by_param.items():
                if len(members) < min_cluster:
                    continue

                if not is_file:
                    child_keys = {
                        m[3][len(prefix)] for m in members if len(m[3]) > len(prefix)
                    }
                    if len(child_keys) < 2:
                        continue
                    if is_root and len(child_keys) >= 4:
                        continue

                types = {m[5] for m in members if m[5]}
                verdict, advisory = _classify_cluster(pname, types, exempt_names)
                scope_str, scope_kind = scope_label(prefix)
                findings.append(
                    FirstParameterCluster(
                        parameter_name=pname,
                        parameter_types=types,
                        members=[(m[0], m[1], m[2]) for m in members],
                        verdict=verdict,
                        advisory=advisory,
                        scope=scope_str,
                        scope_kind=scope_kind,
                    )
                )
                for m in members:
                    claimed.add((m[1], m[0]))

        findings.sort(key=lambda c: (-c.scope.count("/"), -len(c.members)))
        return findings

    def bodies_for_cluster(self, cluster: Any) -> dict[tuple[str, str], tuple[Any, bytes]]:
        """Return the (file, name) -> (body_node, content) map needed by
        the legacy ``_profile_cluster`` helper.

        During the migration window the rule wrapper passes this map
        back into the legacy signal computer; once the body-Jaccard /
        receiver-call density compute methods land here directly
        (follow-up intent), this helper retires.
        """
        out: dict[tuple[str, str], tuple[Any, bytes]] = {}
        for name, file, _line in cluster.members:
            # Find the callable matching (file, simple_name). The qualname
            # ends with simple_name; multiple callables may share the
            # simple name across files — disambiguate by file match.
            for k, c in self._callable_by_key.items():
                if k[1].split(".")[-1] != name:
                    continue
                # Match by relative-file suffix (members carry the relative
                # path from the codebase root; callable.path is absolute).
                if not str(c.path).endswith(file):
                    continue
                node = self._node_by_key.get(k)
                if node is None:
                    continue
                body = node.child_by_field_name("body")
                if body is None:
                    continue
                content = self._content_by_path.get(str(c.path), b"")
                out[(file, name)] = (body, content)
                break
        return out

    # ---- slicing -----------------------------------------------------

    def under(
        self,
        *,
        path: str | None = None,
        qualname: str | None = None,
    ) -> Lexicon:
        """Return a new Lexicon restricted to occurrences under ``path``
        and/or under the qualname-rooted scope ``qualname``."""
        new_filters = list(self._filters)
        if path is not None:
            path_prefix = path
            new_filters.append(lambda rec: str(rec.path).startswith(path_prefix))
        if qualname is not None:
            qn = qualname
            new_filters.append(
                lambda rec: getattr(rec, "qualname", "").startswith(qn)
            )
        return Lexicon(self._parses, filters=tuple(new_filters))

    def where(
        self,
        *,
        language: str | None = None,
        kind: str | None = None,
    ) -> Lexicon:
        """Return a new Lexicon restricted by language and/or occurrence kind.

        Language filter uses the view's internal ``path → language`` map
        since records dropped the denormalised ``language`` field.
        """
        new_filters = list(self._filters)
        if language is not None:
            lang = language
            lang_map = self._language_by_path
            new_filters.append(lambda rec: lang_map.get(str(rec.path)) == lang)
        if kind is not None:
            k = kind
            new_filters.append(lambda rec: getattr(rec, "kind", None) == k)
        return Lexicon(self._parses, filters=tuple(new_filters))

    def walk(self) -> Iterable[Occurrence]:
        """Yield every Occurrence in this view (filtered if sliced)."""
        for p in self._parses:
            for o in p.occurrences:
                if all(f(o) for f in self._filters):
                    yield o


def _common_prefix(paths: list) -> str:
    """Return the longest common directory prefix across paths."""
    import os
    return os.path.commonpath([str(p) for p in paths])
