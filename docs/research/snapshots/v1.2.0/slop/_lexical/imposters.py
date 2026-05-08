"""Imposters kernel — first-parameter clustering with multi-signal profile.

When N functions share a first-parameter name, that parameter is
posing as an ordinary dependency while actually performing some
unifying role. Whether that role is "receiver of methods on a
missing class" or "input to a tabular dispatch family" or
"shared input to unrelated helpers" depends on what the cluster
ACTUALLY does — and that's not visible from the parameter name
alone.

The kernel:

1. Walks every function definition, extracts the first parameter
   name + type via tree-sitter.
2. Clusters by first-parameter name.
3. Walks the namespace tree deepest-first, claiming clusters at
   the narrowest scope where they cohere.
4. **Multi-signal profile** per cluster (v1.2.0 upgrade):
   - Body-shape Jaccard mean (PoC v2.2): pairwise AST 3-gram
     similarity. High score → cluster members do the same thing
     parametrically (clone family).
   - Mean receiver-call density (PoC v2.6): count of
     ``first_param.attr`` and ``first_param[k]`` accesses per
     member. High → members actually treat the parameter as a
     receiver.
5. Profile-aware verdict:
   - ``missing_class`` — receiver-calls high regardless of body
     similarity. Strong recommend: extract a class.
   - ``strategy_family`` — body Jaccard high, receiver-calls zero.
     Members are clones with parametric variation; suppress the
     class-extraction advisory in favour of "consider tabular
     dispatch."
   - ``heterogeneous`` — neither. Cluster is real (shared input)
     but lacks clear unifying behaviour. Surface for review; no
     specific refactor.
   - ``infrastructure`` / ``false_positive`` — preserved from
     v1.1.0 verdict classifier (root/path/node etc.).

PoC references: ``scripts/research/composition_poc/poc3_*.py``,
``scripts/research/composition_poc_v2/poc{2,6}_*.py``.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from slop._lexical._naming import (
    FunctionContext,
    enumerate_functions,
    scope_label,
    split_identifier,
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
    # Multi-signal profile (v1.2.0)
    body_jaccard_mean: float = 0.0        # cluster body-shape cohesion in [0, 1]
    mean_receiver_calls: float = 0.0      # avg `first_param.attr` count per member
    modal_overlap_mean: float = 0.0       # avg member-name overlap with cluster modal tokens
    profile_label: str = "unknown"        # "missing_class" | "strategy_family"
                                          # | "heterogeneous" | "infrastructure"
                                          # | "false_positive"


@dataclass
class ImpostersResult:
    clusters: list[FirstParameterCluster] = field(default_factory=list)
    files_searched: int = 0
    functions_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Multi-signal helpers (PoC v2.2 + v2.6)
# ---------------------------------------------------------------------------


_LEAF_OR_NOISE = frozenset({
    "identifier", "integer", "float", "string", "string_content",
    "true", "false", "none", "comment",
    ":", ",", "(", ")", "[", "]", "{", "}", ".",
    "=", "+", "-", "*", "/", "%", "<", ">", "==", "!=",
    "string_start", "string_end",
})


def _signature_ngrams(node, n: int = 3) -> set[tuple[str, ...]]:
    """AST node-type 3-grams over a function body (PoC v2.2)."""
    seq: list[str] = []

    def walk(nn):
        if nn.type not in _LEAF_OR_NOISE:
            seq.append(nn.type)
        for child in nn.children:
            walk(child)
    walk(node)
    if len(seq) < n:
        return {tuple(seq)} if seq else set()
    return {tuple(seq[i:i + n]) for i in range(len(seq) - n + 1)}


def _receiver_call_count(body, content: bytes, param_name: str) -> int:
    """Count ``param.attr`` and ``param[k]`` references in body
    (PoC v2.6). Proxies "is this parameter being treated as a
    receiver of methods?"."""
    count = 0

    def walk(node):
        nonlocal count
        if node.type == "attribute":
            obj = node.child_by_field_name("object")
            if obj is not None and obj.type == "identifier":
                text = content[obj.start_byte:obj.end_byte].decode(
                    "utf-8", errors="replace",
                )
                if text == param_name:
                    count += 1
        if node.type == "subscript":
            value = node.child_by_field_name("value")
            if value is not None and value.type == "identifier":
                text = content[value.start_byte:value.end_byte].decode(
                    "utf-8", errors="replace",
                )
                if text == param_name:
                    count += 1
        for child in node.children:
            walk(child)
    walk(body)
    return count


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _profile_cluster(
    cluster: FirstParameterCluster,
    bodies: dict[tuple[str, str], tuple],
) -> None:
    """Compute body-shape Jaccard mean, mean receiver-call density,
    and modal-token overlap for a cluster. Mutates the cluster in
    place with the per-cluster signal values + a profile_label."""
    members_with_body = [
        (name, file, line) for name, file, line in cluster.members
        if (file, name) in bodies
    ]
    if len(members_with_body) < 2:
        # Not enough data for cohesion; leave defaults
        return

    sigs: list[tuple[set[tuple[str, ...]], int]] = []
    name_tokens: list[str] = []
    for name, file, _line in members_with_body:
        body_node, content = bodies[(file, name)]
        sigs.append((
            _signature_ngrams(body_node),
            _receiver_call_count(body_node, content, cluster.parameter_name),
        ))
        name_tokens.extend(t.lower() for t in split_identifier(name))

    # Body-shape Jaccard mean across all member pairs
    pair_scores: list[float] = []
    for i in range(len(sigs)):
        for j in range(i + 1, len(sigs)):
            pair_scores.append(_jaccard(sigs[i][0], sigs[j][0]))
    cluster.body_jaccard_mean = (
        sum(pair_scores) / len(pair_scores) if pair_scores else 0.0
    )

    # Receiver-call density mean
    cluster.mean_receiver_calls = (
        sum(rc for _, rc in sigs) / len(sigs) if sigs else 0.0
    )

    # Modal-token overlap mean
    modal = {t for t, _ in Counter(name_tokens).most_common(3)}
    if modal:
        per_member_overlap = []
        for name, _f, _l in members_with_body:
            my_tokens = {t.lower() for t in split_identifier(name)}
            if not my_tokens:
                continue
            per_member_overlap.append(len(my_tokens & modal) / len(my_tokens))
        if per_member_overlap:
            cluster.modal_overlap_mean = (
                sum(per_member_overlap) / len(per_member_overlap)
            )

    # Profile label: combine the signals into a single advisory class.
    # Verdict (v1.1.0 classifier) takes precedence for non-strong
    # cases; multi-signal only refines the strong case.
    if cluster.verdict == "false_positive":
        cluster.profile_label = "false_positive"
    elif cluster.verdict == "weak":
        cluster.profile_label = "infrastructure"
    elif cluster.body_jaccard_mean >= 0.7 and cluster.mean_receiver_calls < 0.5:
        # Members do the same thing N ways without using the param as
        # a receiver — strategy/dispatch family, NOT a missing class.
        cluster.profile_label = "strategy_family"
    elif cluster.mean_receiver_calls >= 1.0:
        # Members actively use the param as a receiver — genuine
        # missing class.
        cluster.profile_label = "missing_class"
    else:
        # Cluster is real (shared input) but profile is mixed: low
        # body cohesion, low receiver-call use. Could be helpers
        # over a config dict, or a cluster of unrelated functions
        # that happen to share an input name.
        cluster.profile_label = "heterogeneous"


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
    bodies: dict[tuple[str, str], tuple] = {}
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
        if ctx.body_node is not None:
            bodies[(ctx.file, ctx.name)] = (ctx.body_node, ctx.content)

    clusters = _recursive_first_param_findings(entries, min_cluster, exempt_names)

    # Multi-signal profile per cluster — body-shape Jaccard,
    # receiver-call density, modal-token overlap.
    for cluster in clusters:
        _profile_cluster(cluster, bodies)

    return ImpostersResult(
        clusters=clusters,
        files_searched=len(files_seen),
        functions_analyzed=total,
    )
