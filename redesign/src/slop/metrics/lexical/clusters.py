"""First-parameter clustering compute. Ported from the legacy
``src/slop/lexicon/clusters.py``, adapted to the v3 scope tree.

Groups callables by their first non-``self``/``cls`` parameter and emits a
``FirstParameterCluster`` at the narrowest scope where the group coheres (the
hierarchical prefix walk is preserved verbatim — it is pure over entries). Each
cluster is then enriched with the multi-signal profile (body Jaccard, receiver-call
density, modal overlap) by ``profile.py``, which reads the raw tree-sitter body node
carried on each v3 callable (``Callable._node`` / ``._content``).

v3 adaptations: entries come from ``Lexical._named_callables`` (not a legacy view
index); parameter *types* are unavailable on the v3 ``Callable`` (annotations are not
retained), so ``parameter_types`` is empty and the type-based classifier branch is a
no-op; per-scope hapax is approximated by the region-wide hapax (the legacy sliced the
view per scope, which the pure-kernel v3 Lexicon does not expose cheaply).
"""
from __future__ import annotations

import os
from typing import Any

from .affix import UNIVERSAL_NOISE, scope_label
from .profile import classify_cluster, profile_cluster
from .records import FirstParameterCluster

# entry: (simple_name, file_rel, line, parts, param_name, param_type)
_Entry = tuple[str, str, int, tuple[str, ...], "str | None", "str | None"]


def compute_first_param_clusters(
    lexical: Any,
    *,
    min_cluster: int = 3,
    exempt_names: frozenset[str] = frozenset({"self", "cls"}),
    root: Any = None,
) -> list[FirstParameterCluster]:
    callables = lexical._named_callables()
    if not callables:
        return []
    paths = [str(c.files[0]) for c in callables if c.files]
    if root is None:
        root = os.path.commonpath(paths) if len(paths) > 1 else (
            os.path.dirname(paths[0]) if paths else "")
    root = str(root)

    isolate_tokens = frozenset(
        t for t, _ in lexical.packet_isolates(
            min_bags=3, min_association=0.7, min_frequency=3, exclude=UNIVERSAL_NOISE)
    )
    spread_map = {t: len(files) for t, files in lexical.token_locations().items()}

    entries = _collect_entries(callables, exempt_names, root)
    findings = _cluster_by_prefix(
        entries, min_cluster=min_cluster, exempt_names=exempt_names,
        isolate_tokens=isolate_tokens, spread_map=spread_map)

    bodies_index = _bodies_index(callables, root)
    scope_hapax = _region_hapax(lexical)
    for cluster in findings:
        bodies = {
            (file, name): bodies_index[(file, name)]
            for name, file, _line in cluster.members
            if (file, name) in bodies_index
        }
        profile_cluster(cluster, bodies, isolate_tokens=isolate_tokens,
                        spread=spread_map, scope_hapax=scope_hapax)
    return findings


def _collect_entries(callables: list[Any], exempt_names: frozenset[str], root: str) -> list[_Entry]:
    entries: list[_Entry] = []
    for c in callables:
        pname: str | None = None
        for p in c.parameters():
            if p in exempt_names:
                continue
            pname = p
            break
        path = str(c.files[0]) if c.files else ""
        file_rel = _rel(path, root)
        parts = tuple(file_rel.split(os.sep)) if file_rel else ()
        simple_name = c.qualname.split(".")[-1]
        entries.append((simple_name, file_rel, _line_of(c), parts, pname, None))
    return entries


def _group_by_param(scope_funcs: list[_Entry]) -> dict[str, list[_Entry]]:
    by_param: dict[str, list[_Entry]] = {}
    for e in scope_funcs:
        pname = e[4]
        if pname is None or len(pname) < 2:
            continue
        by_param.setdefault(pname, []).append(e)
    return by_param


def _param_cluster(prefix, pname, members, *, is_file, is_root,
                   exempt_names, isolate_tokens, spread_map) -> FirstParameterCluster | None:
    if not is_file:
        child_keys = {m[3][len(prefix)] for m in members if len(m[3]) > len(prefix)}
        if len(child_keys) < 2:
            return None
        if is_root and len(child_keys) >= 4:
            return None
    types = {m[5] for m in members if m[5]}
    verdict, advisory = classify_cluster(
        pname, types, exempt_names, isolate_tokens=isolate_tokens, spread=spread_map)
    scope_str, scope_kind = scope_label(prefix)
    return FirstParameterCluster(
        parameter_name=pname, parameter_types=types,
        members=[(m[0], m[1], m[2]) for m in members],
        verdict=verdict, advisory=advisory, scope=scope_str, scope_kind=scope_kind)


def _cluster_by_prefix(entries, *, min_cluster, exempt_names, isolate_tokens, spread_map):
    by_prefix: dict[tuple[str, ...], list[_Entry]] = {(): list(entries)}
    for e in entries:
        parts = e[3]
        for depth in range(1, len(parts) + 1):
            by_prefix.setdefault(parts[:depth], []).append(e)

    findings: list[FirstParameterCluster] = []
    claimed: set[tuple[str, str]] = set()
    for prefix in sorted(by_prefix.keys(), key=lambda p: -len(p)):
        scope_funcs = [e for e in by_prefix[prefix] if (e[1], e[0]) not in claimed]
        if len(scope_funcs) < min_cluster:
            continue
        is_root = not prefix
        is_file = bool(prefix) and "." in prefix[-1]
        for pname, members in _group_by_param(scope_funcs).items():
            if len(members) < min_cluster:
                continue
            cluster = _param_cluster(
                prefix, pname, members, is_file=is_file, is_root=is_root,
                exempt_names=exempt_names, isolate_tokens=isolate_tokens, spread_map=spread_map)
            if cluster is None:
                continue
            findings.append(cluster)
            for m in members:
                claimed.add((m[1], m[0]))
    findings.sort(key=lambda c: (-c.scope.count("/"), -len(c.members)))
    return findings


def _bodies_index(callables: list[Any], root: str) -> dict[tuple[str, str], tuple[Any, bytes, Any]]:
    out: dict[tuple[str, str], tuple[Any, bytes, Any]] = {}
    for c in callables:
        node = getattr(c, "_node", None)
        if node is None:
            continue
        body = node.child_by_field_name("body")
        if body is None:
            continue
        file_rel = _rel(str(c.files[0]) if c.files else "", root)
        out[(file_rel, c.qualname.split(".")[-1])] = (body, c._content, getattr(c, "_grammar", None))
    return out


def _region_hapax(lexical: Any) -> float:
    try:
        return lexical._r.lexicon().hapax_ratio()
    except Exception:
        return 0.0


def _rel(path: str, root: str) -> str:
    if not path:
        return ""
    try:
        return os.path.relpath(path, root) if root else path
    except ValueError:
        return path


def _line_of(c: Any) -> int:
    node = getattr(c, "_node", None)
    if node is not None and getattr(node, "start_point", None) is not None:
        return node.start_point[0] + 1
    return 0
