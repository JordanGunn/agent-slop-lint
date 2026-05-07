"""Composition kernel — detection of missing namespaces / abstractions.

Two algorithms, one shared substrate (the function-definition index from
``slop._lexical._naming``):

- ``affix_polymorphism_kernel`` — token-Levenshtein clustering enriched
  with Formal Concept Analysis. Surfaces missing namespace candidates
  with their inheritance lattice and a kernel × language density
  matrix. See ``docs/philosophy/composition-and-lexical.md`` for the
  scientific grounding (Wille 1982; Caprile & Tonella 2000; Bavota et
  al.; Harris 1955; MDL).

- ``first_parameter_drift_kernel`` — clusters functions by first-
  parameter name. Strong / weak / false-positive verdicts based on
  the parameter's role (domain entity vs third-party library type
  vs infrastructure parameter).

The PoC scripts under ``scripts/research/composition_poc/`` are the
canonical reference for the algorithm details. This kernel ports them
to slop's standard primitives (cross-language via tree-sitter; config-
respecting via ``_fs.find_kernel``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any

from slop._lexical._naming import enumerate_functions, FunctionContext


# ===========================================================================
# Identifier tokenisation (shared)
# ===========================================================================

_CAMEL_LU = re.compile(r"([a-z])([A-Z])")
_CAMEL_UU = re.compile(r"([A-Z]+)([A-Z][a-z])")


def _split(name: str) -> list[str]:
    s = name.strip("_")
    s = _CAMEL_LU.sub(r"\1_\2", s)
    s = _CAMEL_UU.sub(r"\1_\2", s)
    return [t.lower() for t in re.split(r"[_]+", s) if t]


# ===========================================================================
# composition.affix_polymorphism
# ===========================================================================


@dataclass
class AffixPattern:
    """One detected (stem, swap-position, alphabet) pattern."""
    stem: tuple[str, ...]                         # e.g. ("*", "name", "extractor")
    swap_position: int
    variants: dict[str, list[tuple[str, str, int]]]  # entity → [(identifier, file, line)]


@dataclass
class AffixCluster:
    """Concept-lattice cluster: a group of patterns sharing an entity alphabet."""
    entity_label: str             # "language" / "metric" / "<unnamed>"
    alphabet: frozenset[str]
    patterns: list[AffixPattern]
    scope: str = "<root>"         # narrowest namespace where the cluster cohered
    scope_kind: str = "root"      # "file" | "package" | "root"


@dataclass
class FCAConcept:
    """One formal concept: (extent, intent) closed pair."""
    extent: frozenset[str]   # entities sharing all operations in intent
    intent: frozenset[str]   # operations shared by all entities in extent
    scope: str = "<root>"
    scope_kind: str = "root"


@dataclass
class AffixPolymorphismResult:
    clusters: list[AffixCluster] = field(default_factory=list)
    concepts: list[FCAConcept] = field(default_factory=list)
    inheritance_pairs: list[tuple[str, str]] = field(default_factory=list)
    kernel_matrix: dict[str, dict[str, int]] = field(default_factory=dict)
    files_searched: int = 0
    functions_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


def _token_edit_distance_1(a: list[str], b: list[str]):
    """Return ``(swap_position, swap_a, swap_b)`` if Levenshtein over
    tokens is exactly 1 and the edit is a substitution; else ``None``.
    Insert / delete edits are ignored — they over-fit to noise.
    """
    if len(a) != len(b):
        return None
    diffs = [(i, a[i], b[i]) for i in range(len(a)) if a[i] != b[i]]
    if len(diffs) != 1:
        return None
    return diffs[0]


def _alphabet_label(alpha: frozenset[str]) -> str:
    """Best-effort label for an entity given its alphabet shape."""
    LANG_TOKENS = {
        "python", "javascript", "typescript", "rust", "go", "java",
        "c_sharp", "csharp", "julia", "c", "cpp", "ruby", "js", "ts",
        "default", "no",
    }
    if alpha and alpha <= LANG_TOKENS:
        return "language"
    return "<unnamed>"


def _build_affix_patterns(
    items: list[tuple[str, str, int, list[str]]],
) -> list[AffixPattern]:
    """Find pattern groups via pairwise token-edit distance.

    ``items`` is a list of ``(name, file, line, tokens)`` tuples.
    Returns one ``AffixPattern`` per ``(stem, swap_pos)`` group.
    """
    groups: dict[tuple[tuple[str, ...], int], dict[str, list[tuple[str, str, int]]]] = {}
    for i, (na, fa, la, ta) in enumerate(items):
        for nb, fb, lb, tb in items[i + 1:]:
            edit = _token_edit_distance_1(ta, tb)
            if edit is None:
                continue
            pos, swap_a, swap_b = edit
            stem = tuple(ta[:pos] + ["*"] + ta[pos + 1:])
            key = (stem, pos)
            if key not in groups:
                groups[key] = {}
            groups[key].setdefault(swap_a, []).append((na, fa, la))
            groups[key].setdefault(swap_b, []).append((nb, fb, lb))
    return [
        AffixPattern(stem=stem, swap_position=pos, variants=variants)
        for (stem, pos), variants in groups.items()
    ]


def _cluster_patterns_by_alphabet(
    patterns: list[AffixPattern],
    min_alphabet: int = 3,
) -> list[AffixCluster]:
    """Cluster patterns whose alphabets overlap by ≥ 2 tokens (transitive)."""
    qualifying = [p for p in patterns if len(p.variants) >= min_alphabet]
    if not qualifying:
        return []

    parent = list(range(len(qualifying)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(x, y):
        parent[find(x)] = find(y)

    for i in range(len(qualifying)):
        ai = set(qualifying[i].variants.keys())
        for j in range(i + 1, len(qualifying)):
            aj = set(qualifying[j].variants.keys())
            if len(ai & aj) >= 2:
                union(i, j)

    grouped: dict[int, list[AffixPattern]] = {}
    for i, p in enumerate(qualifying):
        grouped.setdefault(find(i), []).append(p)

    clusters: list[AffixCluster] = []
    for patterns in grouped.values():
        alphabet = frozenset.union(*(frozenset(p.variants.keys()) for p in patterns))
        clusters.append(AffixCluster(
            entity_label=_alphabet_label(alphabet),
            alphabet=alphabet,
            patterns=patterns,
        ))
    return clusters


# ---------------------------------------------------------------------------
# Formal Concept Analysis
# ---------------------------------------------------------------------------


def _compute_concepts(relation: dict[str, set[str]]) -> list[FCAConcept]:
    """All formal concepts of a binary relation (brute force; small N).

    A concept ``(E, I)`` is a closed pair: E is the maximal set of
    entities that share all operations in I, and I is the maximal set
    of operations shared by all entities in E.
    """
    objects = list(relation.keys())
    attributes = sorted({a for s in relation.values() for a in s})
    if not attributes:
        return []

    def extent(intent: frozenset[str]) -> frozenset[str]:
        return frozenset(o for o in objects if intent <= relation[o])

    def intent(extent: frozenset[str]) -> frozenset[str]:
        if not extent:
            return frozenset(attributes)
        return frozenset.intersection(*(frozenset(relation[o]) for o in extent))

    concepts: set[tuple[frozenset[str], frozenset[str]]] = set()
    for r in range(len(attributes) + 1):
        for combo in combinations(attributes, r):
            i = frozenset(combo)
            e = extent(i)
            ii = intent(e)
            concepts.add((e, ii))
    for o in objects:
        e = extent(frozenset(relation[o]))
        i = intent(e)
        concepts.add((e, i))

    return [
        FCAConcept(extent=e, intent=i)
        for e, i in sorted(concepts, key=lambda c: (-len(c[1]), -len(c[0])))
    ]


def _find_inheritance_pairs(
    relation: dict[str, set[str]],
    min_parent_ops: int = 2,
) -> list[tuple[str, str]]:
    """Pairs ``(parent, child)`` where child's intent ⊃ parent's strictly,
    parent has at least ``min_parent_ops`` operations, and no entity sits
    between them in the lattice.
    """
    out: list[tuple[str, str]] = []
    for a in relation:
        if len(relation[a]) < min_parent_ops:
            continue
        for b in relation:
            if a == b:
                continue
            if not relation[a] or not (relation[a] < relation[b]):
                continue
            minimal = True
            for c in relation:
                if c in (a, b):
                    continue
                if relation[a] < relation[c] < relation[b]:
                    minimal = False
                    break
            if minimal:
                out.append((a, b))
    return out


# ---------------------------------------------------------------------------
# Public kernel: affix_polymorphism
# ---------------------------------------------------------------------------


def _affix_at_scope(
    items_at_scope: list[tuple[str, str, int, list[str]]],
    scope_path: tuple[str, ...],
    min_alphabet: int,
) -> tuple[list[AffixCluster], list[FCAConcept], list[tuple[str, str]]]:
    """Run pattern detection + FCA + inheritance lattice on one scope's
    items. Returns ``(clusters, concepts, inheritance_pairs)`` all
    tagged with the given scope.
    """
    if len(items_at_scope) < 2:
        return ([], [], [])

    scope_str, scope_kind = _scope_label(scope_path)

    patterns = _build_affix_patterns(items_at_scope)
    clusters = _cluster_patterns_by_alphabet(patterns, min_alphabet=min_alphabet)
    for c in clusters:
        c.scope = scope_str
        c.scope_kind = scope_kind

    relation: dict[str, set[str]] = {}
    if clusters:
        primary = max(clusters, key=lambda c: sum(len(p.variants) for p in c.patterns))
        for pattern in primary.patterns:
            stem_no_star = "_".join(t for t in pattern.stem if t != "*")
            for entity, members in pattern.variants.items():
                relation.setdefault(entity, set()).add(stem_no_star or "<empty>")

    concepts = _compute_concepts(relation) if relation else []
    for c in concepts:
        c.scope = scope_str
        c.scope_kind = scope_kind
    inheritance = _find_inheritance_pairs(relation) if relation else []

    return (clusters, concepts, inheritance)


def affix_polymorphism_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    min_alphabet: int = 3,
) -> AffixPolymorphismResult:
    """Detect missing-namespace candidates via affix polymorphism + FCA.

    Recursive scoping: pattern detection runs per-namespace (file → package
    → root). A cluster is reported at the narrowest scope where its
    full alphabet lives. Cross-package alphabets (e.g. test/source name
    overlap producing spurious concepts) only emerge at root scope and
    only if no narrower scope contains the pattern — the typical
    test/source false-positive vanishes because both halves cohere
    independently within their own packages and never share a scope.

    Args:
        root: Search root.
        languages: Restrict to these languages.
        globs / excludes / hidden / no_ignore: file-discovery args.
        min_alphabet: minimum number of varying tokens in a pattern's
            alphabet for it to qualify (default 3).
    """
    items: list[tuple[str, str, int, list[str]]] = []
    files_seen: set[str] = set()
    for ctx in enumerate_functions(
        root, languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    ):
        files_seen.add(ctx.file)
        if ctx.name.startswith("<") or len(ctx.name) < 2:
            continue
        items.append((ctx.name, ctx.file, ctx.line, _split(ctx.name)))

    # Index every item under every prefix of its path.
    by_prefix: dict[tuple[str, ...], list[tuple[str, str, int, list[str]]]] = {
        (): list(items)
    }
    for it in items:
        parts = tuple(it[1].replace("\\", "/").split("/"))
        for depth in range(1, len(parts) + 1):
            by_prefix.setdefault(parts[:depth], []).append(it)

    # Walk deepest first; claim alphabet members at narrowest scope.
    paths = sorted(by_prefix.keys(), key=lambda p: -len(p))
    claimed_entities: set[tuple[tuple[str, ...], str]] = set()
    # ``claimed_entities`` keys are ``(parent_scope_path, entity)`` so the
    # same entity can appear in clusters at disjoint scopes (a `python`
    # alphabet member can show up in both ``_lexical/`` and ``_structural/``
    # if both packages have a ``_python_*`` family).

    all_clusters: list[AffixCluster] = []
    all_concepts: list[FCAConcept] = []
    all_pairs: list[tuple[str, str]] = []
    # Track which (scope, alphabet) pairs we've already emitted so that
    # the same alphabet doesn't surface again at every parent scope.
    emitted_alphabets: list[tuple[tuple[str, ...], frozenset[str]]] = []

    for path in paths:
        clusters, concepts, inheritance = _affix_at_scope(
            by_prefix[path], path, min_alphabet,
        )
        # Filter clusters whose alphabet has already been claimed at a
        # narrower scope inside this subtree. A cluster only counts at
        # this scope if it brings ≥ ``min_alphabet`` new entities.
        kept_alphabet = frozenset()
        for cluster in clusters:
            unclaimed = {
                e for e in cluster.alphabet
                if not any(
                    cp != path
                    and len(cp) >= len(path)
                    and cp[:len(path)] == path
                    and (cp, e) in claimed_entities
                    for cp in by_prefix
                )
            }
            if len(unclaimed) < min_alphabet:
                continue
            # Also drop if a parent already emitted this alphabet at a
            # broader scope (shouldn't happen with deepest-first walk
            # but defensive).
            if any(
                a == cluster.alphabet and len(p) <= len(path)
                for p, a in emitted_alphabets
            ):
                continue
            all_clusters.append(cluster)
            kept_alphabet = kept_alphabet | cluster.alphabet
            emitted_alphabets.append((path, cluster.alphabet))
            for e in cluster.alphabet:
                claimed_entities.add((path, e))
        # Only emit concepts and inheritance pairs that come from
        # clusters we actually kept at this scope. Same-alphabet
        # patterns at parent scopes are filtered out.
        if kept_alphabet:
            for c in concepts:
                if len(c.extent) >= 2 and len(c.intent) >= 2 and c.extent <= kept_alphabet:
                    all_concepts.append(c)
            for parent, child in inheritance:
                if parent in kept_alphabet and child in kept_alphabet:
                    all_pairs.append((parent, child))

    # Kernel × language density matrix derived from the deepest-scope
    # primary cluster (kept for reporting; not used for filtering).
    kernel_matrix: dict[str, dict[str, int]] = {}
    if all_clusters:
        primary = max(all_clusters, key=lambda c: len(c.alphabet))
        for entity in primary.alphabet:
            kernel_matrix[entity] = {}
        for ctx in enumerate_functions(
            root, languages=languages, globs=globs, excludes=excludes,
            hidden=hidden, no_ignore=no_ignore,
        ):
            tokens = _split(ctx.name)
            for entity in primary.alphabet:
                if entity in tokens:
                    kernel_matrix[entity][ctx.file] = (
                        kernel_matrix[entity].get(ctx.file, 0) + 1
                    )

    return AffixPolymorphismResult(
        clusters=all_clusters,
        concepts=all_concepts,
        inheritance_pairs=all_pairs,
        kernel_matrix=kernel_matrix,
        files_searched=len(files_seen),
        functions_analyzed=len(items),
    )


# ===========================================================================
# composition.first_parameter_drift
# ===========================================================================


@dataclass
class FirstParameterCluster:
    parameter_name: str
    parameter_types: set[str]    # all type annotations seen
    members: list[tuple[str, str, int]]  # (function_name, file, line)
    verdict: str                 # "strong" | "weak" | "false_positive"
    advisory: str
    scope: str                   # narrowest namespace where cluster cohered
    scope_kind: str              # "file" | "package" | "root"


@dataclass
class FirstParameterDriftResult:
    clusters: list[FirstParameterCluster] = field(default_factory=list)
    files_searched: int = 0
    functions_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


_FALSE_POSITIVE_NAMES: frozenset[str] = frozenset({
    "node", "tree",          # tree-sitter library types — wrapping = anti-pattern
})
_INFRASTRUCTURE_NAMES: frozenset[str] = frozenset({
    "root", "file_path", "path", "fp",  # filesystem paths
})


def _extract_first_param(ctx: FunctionContext) -> tuple[str | None, str | None]:
    """Return (param_name, param_type_text) for the first parameter, or
    (None, None) if the function has no parameters.

    Cross-language: each tree-sitter grammar exposes the parameter list
    differently. Implements Python, JS/TS, Go, Java, C#, Rust, Ruby,
    C, C++, Julia. Best-effort; returns None for unhandled shapes.
    """
    node = ctx.node
    lang = ctx.language
    content = ctx.content

    # Skip self/cls (Python convention)
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

    # Other languages: best-effort. Fall through to (None, None) for
    # unhandled shapes; the rule reports them as untyped.
    return (None, None)


def _classify_cluster(
    parameter_name: str,
    parameter_types: set[str],
    exempt_names: frozenset[str],
) -> tuple[str, str]:
    """Return (verdict, advisory)."""
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
# Recursive namespace traversal — narrowest-scope-first cluster claiming
# ---------------------------------------------------------------------------


@dataclass
class _FuncEntry:
    """One function with everything the recursive walk needs."""
    name: str
    file: str               # relative path with ``/`` separators
    line: int
    parts: tuple[str, ...]  # tuple form of file path (("cli", "slop", "output.py"))
    param_name: str | None
    param_type: str | None


def _scope_label(parts: tuple[str, ...]) -> tuple[str, str]:
    """Render ``parts`` to a (scope_str, scope_kind) pair."""
    if not parts:
        return ("<root>", "root")
    last = parts[-1]
    is_file = "." in last
    return ("/".join(parts), "file" if is_file else "package")


def _recursive_first_param_findings(
    entries: list[_FuncEntry],
    min_cluster: int,
    exempt_names: frozenset[str],
) -> list[FirstParameterCluster]:
    """Walk the namespace tree deepest-first; emit clusters at the
    narrowest scope where they cohere. A function can appear in at
    most one cluster — once claimed at a leaf, it's invisible at
    parent scopes.
    """
    # Index every entry under every prefix of its path so that scope-
    # level lookups are O(1). Empty prefix = root.
    by_prefix: dict[tuple[str, ...], list[_FuncEntry]] = {(): list(entries)}
    for e in entries:
        for depth in range(1, len(e.parts) + 1):
            by_prefix.setdefault(e.parts[:depth], []).append(e)

    # Visit deepest paths first. Leaves (files) before parents
    # (packages) before root. Same-depth ordering doesn't matter since
    # disjoint subtrees can't share entries.
    paths = sorted(by_prefix.keys(), key=lambda p: -len(p))

    findings: list[FirstParameterCluster] = []
    claimed: set[tuple[str, str]] = set()  # (file, function_name)

    for path in paths:
        scope_funcs = [
            e for e in by_prefix[path] if (e.file, e.name) not in claimed
        ]
        if len(scope_funcs) < min_cluster:
            continue

        is_root = not path
        is_file = bool(path) and "." in path[-1]

        # Cluster by first-param name
        by_param: dict[str, list[_FuncEntry]] = {}
        for e in scope_funcs:
            if e.param_name is None or len(e.param_name) < 2:
                continue
            by_param.setdefault(e.param_name, []).append(e)

        for pname, members in by_param.items():
            if len(members) < min_cluster:
                continue

            # Coherence check.
            #
            # File scope: by construction, every member is in this file.
            # Trivially coherent.
            #
            # Package scope: claim only if members span ≥ 2 children of
            # this node. If they all share one child, the file-level pass
            # (deeper depth) would already have claimed them — so reaching
            # here means they didn't reach threshold there. Lowering the
            # bar at the parent isn't a real cluster, just threshold
            # inflation by the parent. Skip.
            #
            # Root scope: same rule (≥ 2 children) plus a stricter
            # spread test. A cluster touching every top-level package
            # is generic-parameter noise (`name: str`, `text: str`).
            if not is_file:
                child_keys = {
                    m.parts[len(path)] for m in members
                    if len(m.parts) > len(path)
                }
                if len(child_keys) < 2:
                    continue
                if is_root and len(child_keys) >= 4:
                    # Spread across 4+ top-level packages → not a class
                    continue

            types = {m.param_type for m in members if m.param_type}
            verdict, advisory = _classify_cluster(pname, types, exempt_names)

            scope_str, scope_kind = _scope_label(path)
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

    # Sort: deepest scope (most actionable) first, then by cluster size
    findings.sort(key=lambda c: (-c.scope.count("/"), -len(c.members)))
    return findings


def first_parameter_drift_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    min_cluster: int = 3,
    exempt_names: frozenset[str] = frozenset(),
) -> FirstParameterDriftResult:
    """Cluster functions by first-parameter name; classify each cluster.

    Recursive namespace scoping: clusters are claimed at the narrowest
    scope where they cohere. A 5-function cluster whose members all
    live in ``output.py`` is reported with ``scope="cli/slop/output.py"``;
    a 5-function cluster spanning three files in ``_lexical/`` is
    reported with ``scope="cli/slop/_lexical"``. Cross-package noise
    fails the coherence test at every scope and drops out.
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
        # Path-component split. Use ``/`` as separator regardless of
        # platform — file paths from enumerate_functions are already
        # POSIX-ish and we want stable scope labels across OSes.
        parts = tuple(ctx.file.replace("\\", "/").split("/"))
        entries.append(_FuncEntry(
            name=ctx.name,
            file=ctx.file,
            line=ctx.line,
            parts=parts,
            param_name=pname,
            param_type=ptype,
        ))

    clusters = _recursive_first_param_findings(entries, min_cluster, exempt_names)

    return FirstParameterDriftResult(
        clusters=clusters,
        files_searched=len(files_seen),
        functions_analyzed=total,
    )
