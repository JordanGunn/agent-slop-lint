"""First-parameter clustering compute for the Lexicon view.

``Lexicon.first_param_clusters`` groups callables by their first
(non-``self``/``cls``) parameter and emits a ``FirstParameterCluster``
at the narrowest scope where the group coheres. The hierarchical
prefix walk, the multi-signal enrichment, and the body-lookup helper
grew past the inline-on-the-view threshold, so they live here as a
delegated algorithm module; the view method is a thin delegator.

The compute reaches into a few of the view's private indexes
(``_callable_by_key`` / ``_node_by_key`` / ``_content_by_path``) and its
``_restricted`` slicer — it is a same-package collaborator of the view,
not an external consumer.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from slop.lexicon.affix import scope_label


def compute_first_param_clusters(
    view: Any,
    *,
    min_cluster: int = 3,
    exempt_names: frozenset[str] = frozenset({"self", "cls"}),
    root: Any = None,
) -> list[Any]:
    """Group callables by first parameter; emit clusters at the narrowest
    scope where they cohere.

    Returns ``FirstParameterCluster`` instances. Hierarchical traversal:
    a callable appears in at most one cluster, claimed at the deepest
    scope where the cluster reaches ``min_cluster``.

    ``root`` is the codebase root used to derive relative paths for the
    path-parts decomposition that drives scope claiming. If None, falls
    back to the longest common prefix across observed callable paths.
    """
    from slop.lexicon.profile import classify_cluster, profile_cluster
    from slop.lexicon.records import FirstParameterCluster
    from slop.lexicon.affix import UNIVERSAL_NOISE
    from slop.tree.records import CallableKind

    # Distribution signals for the classifier: packet isolates (frequent
    # tokens that don't co-occur with partners) and per-token file spread.
    isolate_tokens = frozenset(
        t for t, _ in view.packet_isolates(
            min_bags=3, min_association=0.7,
            min_frequency=3, exclude=UNIVERSAL_NOISE,
        )
    )
    spread_map = {
        t: len(files)
        for t, files in view.token_locations(exclude=UNIVERSAL_NOISE).items()
    }

    if root is None:
        # Best-effort: derive from common prefix.
        paths = [c.path for c in view._callable_by_key.values()]  # noqa: SLF001
        if paths:
            try:
                root = Path(_common_prefix(paths))
            except Exception:
                root = paths[0].parent
        else:
            return []
    root_path = Path(root)

    # entries: list of (name, file_rel, line, parts, param_name, param_type)
    entries: list[tuple[str, str, int, tuple[str, ...], str | None, str | None]] = []
    for c in view._callable_by_key.values():  # noqa: SLF001
        if not all(f(c) for f in view._filters):  # noqa: SLF001
            continue
        # Lambdas are excluded from first-parameter clustering. Their
        # first parameter is typically a closure variable, not a
        # receiver candidate.
        if c.kind == CallableKind.LAMBDA:
            continue
        # Skip "self"/"cls" first parameters for methods
        pname: str | None = None
        ptype: str | None = None
        for p in c.parameters:
            if p.name in exempt_names:
                continue
            pname = p.name
            ptype = p.annotation
            break
        try:
            rel = c.path.relative_to(root_path)
            parts = rel.parts
            file_rel = str(rel)
        except ValueError:
            parts = c.path.parts
            file_rel = str(c.path)
        # Use simple base-name (without qualname prefix) for member naming.
        simple_name = c.qualname.split(".")[-1]
        entries.append((simple_name, file_rel, c.line, parts, pname, ptype))

    # Hierarchical clustering by path prefix.
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
            verdict, advisory = classify_cluster(
                pname, types, exempt_names,
                isolate_tokens=isolate_tokens,
                spread=spread_map,
            )
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

    # Enrich each cluster with multi-signal profile (body Jaccard,
    # receiver-call density, modal-token overlap). Per-cluster
    # hapax_ratio is cached by scope to avoid recomputation.
    cache: dict[str, float] = {}

    def _scope_hapax(cluster: Any) -> float:
        scope_key = f"{cluster.scope_kind}:{cluster.scope}"
        if scope_key in cache:
            return cache[scope_key]
        if cluster.scope_kind == "file":
            scoped = view._restricted(  # noqa: SLF001
                lambda rec, sc=cluster.scope: str(rec.path).endswith(sc),
            )
        elif cluster.scope_kind == "package":
            scoped = view._restricted(  # noqa: SLF001
                lambda rec, sc=cluster.scope: sc in str(rec.path),
            )
        else:
            scoped = view
        ratio = scoped.hapax_ratio(exclude=UNIVERSAL_NOISE)
        cache[scope_key] = ratio
        return ratio

    for cluster in findings:
        bodies = _bodies_for_cluster(view, cluster)
        profile_cluster(
            cluster, bodies,
            isolate_tokens=isolate_tokens,
            spread=spread_map,
            scope_hapax=_scope_hapax(cluster),
        )

    return findings


def _bodies_for_cluster(view: Any, cluster: Any) -> dict[tuple[str, str], tuple[Any, bytes]]:
    """Return the ``(file, name) -> (body_node, content)`` map the
    cluster profiler walks for body-Jaccard / receiver-call density.
    """
    out: dict[tuple[str, str], tuple[Any, bytes]] = {}
    for name, file, _line in cluster.members:
        # Find the callable matching (file, simple_name). The qualname
        # ends with simple_name; multiple callables may share the simple
        # name across files — disambiguate by file match.
        for k, c in view._callable_by_key.items():  # noqa: SLF001
            if k[1].split(".")[-1] != name:
                continue
            # Match by relative-file suffix (members carry the relative
            # path from the codebase root; callable.path is absolute).
            if not str(c.path).endswith(file):
                continue
            node = view._node_by_key.get(k)  # noqa: SLF001
            if node is None:
                continue
            body = node.child_by_field_name("body")
            if body is None:
                continue
            content = view._content_by_path.get(str(c.path), b"")  # noqa: SLF001
            out[(file, name)] = (body, content)
            break
    return out


def _common_prefix(paths: list) -> str:
    """Return the longest common directory prefix across paths."""
    import os
    return os.path.commonpath([str(p) for p in paths])
