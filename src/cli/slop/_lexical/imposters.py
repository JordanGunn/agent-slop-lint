"""Imposters kernel — first-parameter clustering.

When N functions share a first parameter name, that parameter is
posing as an ordinary dependency while actually performing the
role of a receiver. The function signature ``def render(canvas,
...)`` makes ``canvas`` LOOK like any other dependency, but the
parameter's repeated appearance across N functions reveals a
hidden receiver-of-method.

This kernel:

1. Walks every function definition, extracts the first parameter
   name + type via tree-sitter.
2. Clusters by first-parameter name.
3. Walks the namespace tree deepest-first, claiming clusters at
   the narrowest scope where they cohere.
4. Classifies each cluster as strong / weak / false_positive
   based on parameter semantics (domain entity vs infrastructure
   vs third-party type).

Phase 3 of the v1.2 plan replaces this single-signal classifier
with multi-signal scoring (body-shape Jaccard + receiver-call
density + modal-token overlap). For now the kernel preserves the
v1.1.0 verdict shape so the rule wrapper layers on top.

PoC reference: ``scripts/research/composition_poc/poc3_first_parameter_drift.py``
and ``scripts/research/composition_poc_v2/poc6_multi_criteria_rank.py``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop._lexical._naming import (
    FunctionContext,
    enumerate_functions,
    scope_label,
)


# ---------------------------------------------------------------------------
# Result classes
# ---------------------------------------------------------------------------


@dataclass
class FirstParameterCluster:
    parameter_name: str
    parameter_types: set[str]
    members: list[tuple[str, str, int]]  # (function_name, file, line)
    verdict: str                          # "strong" | "weak" | "false_positive"
    advisory: str
    scope: str
    scope_kind: str                       # "file" | "package" | "root"


@dataclass
class ImpostersResult:
    clusters: list[FirstParameterCluster] = field(default_factory=list)
    files_searched: int = 0
    functions_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Verdict-classification heuristics
# ---------------------------------------------------------------------------


_FALSE_POSITIVE_NAMES: frozenset[str] = frozenset({
    "node", "tree",          # tree-sitter library types
})
_INFRASTRUCTURE_NAMES: frozenset[str] = frozenset({
    "root", "file_path", "path", "fp",
})


def _classify_cluster(
    parameter_name: str,
    parameter_types: set[str],
    exempt_names: frozenset[str],
) -> tuple[str, str]:
    """Return ``(verdict, advisory)``."""
    if parameter_name in _FALSE_POSITIVE_NAMES or parameter_name in exempt_names:
        return ("false_positive",
                f"`{parameter_name}` is typically a third-party library "
                f"type or otherwise marked exempt; wrapping it in a slop "
                f"class would create an adapter layer with no clear "
                f"benefit.")
    if parameter_name in _INFRASTRUCTURE_NAMES:
        return ("weak",
                f"`{parameter_name}` is an infrastructure parameter "
                f"(filesystem path / scan root). The cluster reflects "
                f"shared configuration plumbing, not a missing class.")
    return ("strong",
            f"`{parameter_name}` is the natural receiver of these "
            f"methods. Folding them into a class with `{parameter_name}` "
            f"as ``self`` is the textbook conversion.")


# ---------------------------------------------------------------------------
# Per-language first-param extraction
# ---------------------------------------------------------------------------


def _extract_first_param(ctx: FunctionContext) -> tuple[str | None, str | None]:
    """Return ``(param_name, param_type_text)`` for the first parameter.

    Cross-language: each tree-sitter grammar exposes the parameter
    list differently. Implements Python today; other languages
    return ``(None, None)`` (cluster signal still works on any
    language whose parameter list slop can read; Python is the
    primary corpus).
    """
    node = ctx.node
    lang = ctx.language
    content = ctx.content

    def _maybe_skip_self(name: str | None) -> bool:
        return name in ("self", "cls")

    if lang == "python":
        params = node.child_by_field_name("parameters")
        if params is None:
            return (None, None)
        for child in params.children:
            ctype = child.type
            if ctype in ("(", ")", ","):
                continue
            if ctype == "identifier":
                name = content[child.start_byte:child.end_byte].decode(errors="replace")
                if _maybe_skip_self(name):
                    continue
                return (name, None)
            if ctype in ("typed_parameter", "typed_default_parameter"):
                name_n = child.child_by_field_name("name") or next(
                    (c for c in child.children if c.type == "identifier"), None,
                )
                type_n = child.child_by_field_name("type")
                if name_n is None:
                    continue
                name = content[name_n.start_byte:name_n.end_byte].decode(errors="replace")
                if _maybe_skip_self(name):
                    continue
                ptype = (
                    content[type_n.start_byte:type_n.end_byte].decode(errors="replace")
                    if type_n is not None else None
                )
                return (name, ptype)
            if ctype == "default_parameter":
                name_n = child.child_by_field_name("name")
                if name_n:
                    name = content[name_n.start_byte:name_n.end_byte].decode(errors="replace")
                    if _maybe_skip_self(name):
                        continue
                    return (name, None)
        return (None, None)

    return (None, None)


# ---------------------------------------------------------------------------
# Recursive namespace traversal — narrowest-scope-first cluster claiming
# ---------------------------------------------------------------------------


@dataclass
class _FuncEntry:
    """One function with everything the recursive walk needs."""
    name: str
    file: str
    line: int
    parts: tuple[str, ...]
    param_name: str | None
    param_type: str | None


def _recursive_first_param_findings(
    entries: list[_FuncEntry],
    min_cluster: int,
    exempt_names: frozenset[str],
) -> list[FirstParameterCluster]:
    """Walk the namespace tree deepest-first; emit clusters at the
    narrowest scope where they cohere. A function appears in at
    most one cluster — once claimed at a leaf, it's invisible at
    parent scopes."""
    by_prefix: dict[tuple[str, ...], list[_FuncEntry]] = {(): list(entries)}
    for e in entries:
        for depth in range(1, len(e.parts) + 1):
            by_prefix.setdefault(e.parts[:depth], []).append(e)

    paths = sorted(by_prefix.keys(), key=lambda p: -len(p))

    findings: list[FirstParameterCluster] = []
    claimed: set[tuple[str, str]] = set()

    for path in paths:
        scope_funcs = [
            e for e in by_prefix[path] if (e.file, e.name) not in claimed
        ]
        if len(scope_funcs) < min_cluster:
            continue

        is_root = not path
        is_file = bool(path) and "." in path[-1]

        by_param: dict[str, list[_FuncEntry]] = {}
        for e in scope_funcs:
            if e.param_name is None or len(e.param_name) < 2:
                continue
            by_param.setdefault(e.param_name, []).append(e)

        for pname, members in by_param.items():
            if len(members) < min_cluster:
                continue

            # Coherence check: at file scope, every member is in this
            # file by construction. At package scope, members must
            # span ≥ 2 children (otherwise file-level pass would have
            # claimed them; reaching the parent means threshold
            # inflation, not a real cluster). At root scope, also
            # require members not to spread across ≥ 4 top-level
            # packages (generic-parameter noise).
            if not is_file:
                child_keys = {
                    m.parts[len(path)] for m in members
                    if len(m.parts) > len(path)
                }
                if len(child_keys) < 2:
                    continue
                if is_root and len(child_keys) >= 4:
                    continue

            types = {m.param_type for m in members if m.param_type}
            verdict, advisory = _classify_cluster(pname, types, exempt_names)

            scope_str, scope_kind = scope_label(path)
            findings.append(FirstParameterCluster(
                parameter_name=pname,
                parameter_types=types,
                members=[(m.name, m.file, m.line) for m in members],
                verdict=verdict,
                advisory=advisory,
                scope=scope_str,
                scope_kind=scope_kind,
            ))
            for m in members:
                claimed.add((m.file, m.name))

    findings.sort(key=lambda c: (-c.scope.count("/"), -len(c.members)))
    return findings


def imposters_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    min_cluster: int = 3,
    exempt_names: frozenset[str] = frozenset(),
) -> ImpostersResult:
    """Cluster functions by first-parameter name; classify per cluster.

    Recursive namespace scoping: clusters claimed at narrowest scope
    where they cohere. A 5-function cluster all in ``output.py`` is
    reported with ``scope="cli/slop/output.py"``; spanning three
    files in ``_lexical/`` is reported with ``scope="cli/slop/_lexical"``.
    Cross-package noise fails the coherence test and drops out.
    """
    entries: list[_FuncEntry] = []
    files_seen: set[str] = set()
    total = 0
    for ctx in enumerate_functions(
        root, languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    ):
        files_seen.add(ctx.file)
        total += 1
        pname, ptype = _extract_first_param(ctx)
        parts = tuple(ctx.file.replace("\\", "/").split("/"))
        entries.append(_FuncEntry(
            name=ctx.name, file=ctx.file, line=ctx.line,
            parts=parts, param_name=pname, param_type=ptype,
        ))

    clusters = _recursive_first_param_findings(entries, min_cluster, exempt_names)

    return ImpostersResult(
        clusters=clusters,
        files_searched=len(files_seen),
        functions_analyzed=total,
    )
