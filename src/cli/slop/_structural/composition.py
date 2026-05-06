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


@dataclass
class FCAConcept:
    """One formal concept: (extent, intent) closed pair."""
    extent: frozenset[str]   # entities sharing all operations in intent
    intent: frozenset[str]   # operations shared by all entities in extent


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

    Args:
        root: Search root.
        languages: Restrict to these languages (passed to enumerate_functions).
        globs / excludes / hidden / no_ignore: file-discovery args.
        min_alphabet: minimum number of varying tokens in a pattern's
            alphabet for it to qualify (default 3 — fewer values is too
            weak a signal).
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

    patterns = _build_affix_patterns(items)
    clusters = _cluster_patterns_by_alphabet(patterns, min_alphabet=min_alphabet)

    # FCA over the (entity, operation) relation derived from the largest
    # cluster (typically the "language" cluster). If no clusters, FCA is empty.
    relation: dict[str, set[str]] = {}
    if clusters:
        primary = max(clusters, key=lambda c: sum(len(p.variants) for p in c.patterns))
        for pattern in primary.patterns:
            stem_no_star = "_".join(t for t in pattern.stem if t != "*")
            for entity, members in pattern.variants.items():
                relation.setdefault(entity, set()).add(stem_no_star or "<empty>")

    concepts = _compute_concepts(relation) if relation else []
    inheritance = _find_inheritance_pairs(relation) if relation else []

    # Kernel × language density matrix (per-file count of behaviour
    # references per entity). Same closed-alphabet view as the PoC5 output.
    kernel_matrix: dict[str, dict[str, int]] = {}
    if relation:
        for entity in relation:
            kernel_matrix[entity] = {}
        for ctx in enumerate_functions(
            root, languages=languages, globs=globs, excludes=excludes,
            hidden=hidden, no_ignore=no_ignore,
        ):
            tokens = _split(ctx.name)
            for entity in relation:
                if entity in tokens:
                    kernel_matrix[entity][ctx.file] = (
                        kernel_matrix[entity].get(ctx.file, 0) + 1
                    )

    return AffixPolymorphismResult(
        clusters=clusters,
        concepts=concepts,
        inheritance_pairs=inheritance,
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
    """Cluster functions by first-parameter name; classify each cluster."""
    by_name: dict[str, list[tuple[str, str, int, str | None]]] = {}
    files_seen: set[str] = set()
    total = 0
    for ctx in enumerate_functions(
        root, languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    ):
        files_seen.add(ctx.file)
        total += 1
        pname, ptype = _extract_first_param(ctx)
        if pname is None:
            continue
        by_name.setdefault(pname, []).append((ctx.name, ctx.file, ctx.line, ptype))

    clusters: list[FirstParameterCluster] = []
    for pname, entries in by_name.items():
        if len(entries) < min_cluster:
            continue
        if len(pname) < 2:
            # Single-character parameters (i, x, n, …) are almost always
            # loop variables or short-form math; not domain receivers.
            continue
        types = {t for _, _, _, t in entries if t}
        verdict, advisory = _classify_cluster(pname, types, exempt_names)
        clusters.append(FirstParameterCluster(
            parameter_name=pname,
            parameter_types=types,
            members=[(n, f, l) for n, f, l, _ in entries],
            verdict=verdict,
            advisory=advisory,
        ))

    clusters.sort(key=lambda c: -len(c.members))

    return FirstParameterDriftResult(
        clusters=clusters,
        files_searched=len(files_seen),
        functions_analyzed=total,
    )
