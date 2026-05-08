"""Sprawl kernel — closed-alphabet detection within / across scope.

When N identifiers in some scope share a stem with one position
varying over a closed set of values, the names are encoding a type
the codebase hasn't declared. ``_python_extract``, ``_java_extract``,
``_csharp_extract`` is the textbook case: the alphabet
``{python, java, csharp}`` is the implicit type, sprawled across
function-name positions instead of declared.

Detection algorithm:

1. Token-Levenshtein-1 affix-pattern grouping (Caprile & Tonella
   2000): pairs of identifiers whose tokenisations differ in
   exactly one position cluster into an ``AffixPattern`` keyed by
   the common stem.
2. Alphabet clustering: patterns sharing ≥ 2 alphabet members
   merge transitively into ``AffixCluster``.
3. Recursive namespace scoping: pattern detection runs at file
   scope, then package scope, then root, claiming alphabet
   members at the narrowest scope where the pattern coheres.
4. Formal Concept Analysis (Wille 1982; Ganter & Wille 1999):
   FCA over the (entity, operation) relation derived from the
   primary cluster surfaces the inheritance lattice — pairs
   ``(parent, child)`` where every operation the parent overrides
   is also overridden by the child.

The PoC under ``scripts/research/composition_poc/poc1*.py`` and the
v2 PoC ``scripts/research/composition_poc_v2/poc4_within_cluster_affix.py``
are the canonical algorithm references.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

from slop._lexical._naming import enumerate_functions, scope_label
from slop._lexical._words import Lexeme


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AffixPattern:
    """One detected (stem, swap-position, alphabet) pattern."""
    stem: tuple[str, ...]                         # e.g. ("*", "name", "extractor")
    swap_position: int
    variants: dict[str, list[tuple[str, str, int]]]  # entity → [(identifier, file, line)]


@dataclass
class AffixCluster:
    """Concept-lattice cluster: a group of patterns sharing an entity alphabet."""
    entity_label: str
    alphabet: frozenset[str]
    patterns: list[AffixPattern]
    scope: str = "<root>"
    scope_kind: str = "root"


@dataclass
class FCAConcept:
    """One formal concept: (extent, intent) closed pair."""
    extent: frozenset[str]
    intent: frozenset[str]
    scope: str = "<root>"
    scope_kind: str = "root"


@dataclass
class SprawlResult:
    clusters: list[AffixCluster] = field(default_factory=list)
    concepts: list[FCAConcept] = field(default_factory=list)
    inheritance_pairs: list[tuple[str, str]] = field(default_factory=list)
    kernel_matrix: dict[str, dict[str, int]] = field(default_factory=dict)
    files_searched: int = 0
    functions_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------


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


def _build_affix_patterns(items: list[Lexeme]) -> list[AffixPattern]:
    """Find pattern groups via pairwise token-edit distance.

    Returns one ``AffixPattern`` per ``(stem, swap_pos)`` group.
    Each Lexeme contributes its ``text``/``file``/``line`` triple
    when its tokenisation differs from a peer in exactly one position.
    """
    groups: dict[tuple[tuple[str, ...], int], dict[str, list[tuple[str, str, int]]]] = {}
    for i, lex_a in enumerate(items):
        toks_a = list(lex_a.lower)
        for lex_b in items[i + 1:]:
            toks_b = list(lex_b.lower)
            edit = _token_edit_distance_1(toks_a, toks_b)
            if edit is None:
                continue
            pos, swap_a, swap_b = edit
            stem = tuple(toks_a[:pos] + ["*"] + toks_a[pos + 1:])
            key = (stem, pos)
            if key not in groups:
                groups[key] = {}
            groups[key].setdefault(swap_a, []).append(
                (lex_a.text, lex_a.file or "", lex_a.line or 0),
            )
            groups[key].setdefault(swap_b, []).append(
                (lex_b.text, lex_b.file or "", lex_b.line or 0),
            )
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
    for cluster_patterns in grouped.values():
        alphabet = frozenset.union(*(frozenset(p.variants.keys()) for p in cluster_patterns))
        clusters.append(AffixCluster(
            entity_label=_alphabet_label(alphabet),
            alphabet=alphabet,
            patterns=cluster_patterns,
        ))
    return clusters


# ---------------------------------------------------------------------------
# Formal Concept Analysis
# ---------------------------------------------------------------------------


def _compute_concepts(relation: dict[str, set[str]]) -> list[FCAConcept]:
    """All formal concepts of a binary relation (brute force; small N)."""
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
    """Pairs ``(parent, child)`` where child's intent ⊃ parent's
    strictly, parent has ≥ ``min_parent_ops`` ops, and no entity sits
    between them in the lattice."""
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
# Per-scope detection
# ---------------------------------------------------------------------------


def _affix_at_scope(
    items_at_scope: list[Lexeme],
    scope_path: tuple[str, ...],
    min_alphabet: int,
) -> tuple[list[AffixCluster], list[FCAConcept], list[tuple[str, str]]]:
    """Run pattern detection + FCA + inheritance lattice on one scope's items."""
    if len(items_at_scope) < 2:
        return ([], [], [])

    scope_str, scope_kind = scope_label(scope_path)

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


def sprawl_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    min_alphabet: int = 3,
) -> SprawlResult:
    """Detect closed-alphabet sprawl in identifier templates.

    Walks file → package → root, claiming alphabet members at the
    narrowest scope where the pattern coheres. Reports per-scope
    clusters, formal concepts, and inheritance lattice pairs.
    """
    items: list[Lexeme] = []
    files_seen: set[str] = set()
    for ctx in enumerate_functions(
        root, languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    ):
        files_seen.add(ctx.file)
        if ctx.name.startswith("<") or len(ctx.name) < 2:
            continue
        items.append(Lexeme.of(ctx.name, file=ctx.file, line=ctx.line))

    by_prefix: dict[tuple[str, ...], list[Lexeme]] = {(): list(items)}
    for it in items:
        parts = tuple((it.file or "").replace("\\", "/").split("/"))
        for depth in range(1, len(parts) + 1):
            by_prefix.setdefault(parts[:depth], []).append(it)

    paths = sorted(by_prefix.keys(), key=lambda p: -len(p))
    claimed_entities: set[tuple[tuple[str, ...], str]] = set()

    all_clusters: list[AffixCluster] = []
    all_concepts: list[FCAConcept] = []
    all_pairs: list[tuple[str, str]] = []
    emitted_alphabets: list[tuple[tuple[str, ...], frozenset[str]]] = []

    for path in paths:
        clusters, concepts, inheritance = _affix_at_scope(
            by_prefix[path], path, min_alphabet,
        )
        kept_alphabet: frozenset[str] = frozenset()
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
        if kept_alphabet:
            for c in concepts:
                if len(c.extent) >= 2 and len(c.intent) >= 2 and c.extent <= kept_alphabet:
                    all_concepts.append(c)
            for parent, child in inheritance:
                if parent in kept_alphabet and child in kept_alphabet:
                    all_pairs.append((parent, child))

    kernel_matrix: dict[str, dict[str, int]] = {}
    if all_clusters:
        primary = max(all_clusters, key=lambda c: len(c.alphabet))
        for entity in primary.alphabet:
            kernel_matrix[entity] = {}
        for ctx in enumerate_functions(
            root, languages=languages, globs=globs, excludes=excludes,
            hidden=hidden, no_ignore=no_ignore,
        ):
            tokens = Lexeme.of(ctx.name).lower
            for entity in primary.alphabet:
                if entity in tokens:
                    kernel_matrix[entity][ctx.file] = (
                        kernel_matrix[entity].get(ctx.file, 0) + 1
                    )

    return SprawlResult(
        clusters=all_clusters,
        concepts=all_concepts,
        inheritance_pairs=all_pairs,
        kernel_matrix=kernel_matrix,
        files_searched=len(files_seen),
        functions_analyzed=len(items),
    )
