"""Affix-pattern + alphabet-clustering + FCA primitives.

Shared by lexical.sprawl (its own algorithm) and lexical.slackers
(uses ``build_affix_patterns`` to decide whether a first-parameter
cluster has a coherent naming template). The Lexicon view consumes
these via the rules; they are not exposed as view methods because
their inputs are caller-shaped (a particular Lexeme list at a
chosen scope).

Algorithm references:
- Caprile & Tonella (2000) — token-Levenshtein-1 affix patterns
- Wille (1982); Ganter & Wille (1999) — Formal Concept Analysis

Token tokenisation uses ``Lexicon.split_tokens``; ``UNIVERSAL_NOISE``
is the layered ignore set (Newman 14 + English glue) from
``docs/research/identifier-vocabulary.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# Newman, AlSuhaibani, Collard & Maletic (SANER 2017) — 14 identifiers
# found in all 50 OSS C/C++ systems they studied.
_NEWMAN_14: frozenset[str] = frozenset({
    "a", "length", "id", "pos", "start", "next", "str", "key",
    "f", "x", "index", "p", "left", "result",
})

# English glue words that appear between meaningful tokens in
# identifier streams (``count_of_items``, ``data_for_id``).
_GLUE: frozenset[str] = frozenset({
    "the", "an", "is", "are", "to", "for", "in", "on", "of",
    "with", "by", "as", "at", "and", "or", "but", "if",
})

UNIVERSAL_NOISE: frozenset[str] = _NEWMAN_14 | _GLUE
"""Layer 1 + Layer 3 of the layered ignore model. SE-boilerplate
(Layer 2: ``manager``, ``helper``, ...) is excluded — that vocabulary
is the signal ``lexical.hammers`` exists to detect."""


@dataclass(frozen=True, slots=True)
class Lexeme:
    """One tokenised identifier with optional source-location metadata.

    Lightweight record passed to ``build_affix_patterns``. Build via
    ``Lexeme.of(text, file=..., line=...)`` to tokenise once.
    """

    text: str
    tokens: tuple[str, ...]
    lower: tuple[str, ...]
    file: str | None = None
    line: int | None = None

    @classmethod
    def of(
        cls,
        text: str,
        *,
        file: str | None = None,
        line: int | None = None,
    ) -> "Lexeme":
        from slop.lexicon.tokenize import split_tokens
        toks = split_tokens(text)
        return cls(
            text=text,
            tokens=toks,
            lower=tuple(t.lower() for t in toks),
            file=file,
            line=line,
        )


@dataclass
class AffixPattern:
    """One detected ``(stem, swap-position, alphabet)`` pattern.

    ``stem`` is the token list with the swap position marked ``*``.
    ``variants`` maps each alphabet member to the source identifiers
    that contributed it (carrying file + line for finding anchors).
    """
    stem: tuple[str, ...]
    swap_position: int
    variants: dict[str, list[tuple[str, str, int]]]


@dataclass
class AffixCluster:
    """A group of patterns sharing an entity alphabet (transitive overlap)."""
    entity_label: str
    alphabet: frozenset[str]
    patterns: list[AffixPattern]
    scope: str = "<root>"
    scope_kind: str = "root"


@dataclass
class FCAConcept:
    """One formal concept: closed ``(extent, intent)`` pair."""
    extent: frozenset[str]
    intent: frozenset[str]
    scope: str = "<root>"
    scope_kind: str = "root"
    #: Relative source files of the identifiers contributing to ``extent`` — the
    #: basis for resolving the concept to a scope locus. Empty if untracked.
    files: frozenset[str] = field(default_factory=frozenset)


def scope_label(parts: tuple[str, ...]) -> tuple[str, str]:
    """Render a path-parts tuple to ``(scope_str, scope_kind)``.

    Examples::

        ()                            -> ("<root>", "root")
        ("cli", "slop")               -> ("cli/slop", "package")
        ("cli", "slop", "output.py")  -> ("cli/slop/output.py", "file")
    """
    if not parts:
        return ("<root>", "root")
    last = parts[-1]
    is_file = "." in last
    return ("/".join(parts), "file" if is_file else "package")


def token_edit_distance_1(a: list[str], b: list[str]):
    """Return ``(swap_position, swap_a, swap_b)`` if Levenshtein over
    tokens is exactly 1 (substitution); else ``None``. Insert / delete
    edits are ignored — they over-fit to noise."""
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


def build_affix_patterns(
    items: list[Lexeme],
    exclude: frozenset[str] = frozenset(),
) -> list[AffixPattern]:
    """Find pattern groups via pairwise token-edit distance.

    Returns one ``AffixPattern`` per ``(stem, swap_pos)`` group.
    Tokens in ``exclude`` are stripped before edit-distance — useful
    when generic identifier noise would otherwise inflate alphabets
    with low-signal variants.
    """
    def _tokens(lex: Lexeme) -> list[str]:
        return [t for t in lex.lower if t not in exclude] if exclude else list(lex.lower)

    groups: dict[tuple[tuple[str, ...], int], dict[str, list[tuple[str, str, int]]]] = {}
    for i, lex_a in enumerate(items):
        toks_a = _tokens(lex_a)
        for lex_b in items[i + 1:]:
            toks_b = _tokens(lex_b)
            edit = token_edit_distance_1(toks_a, toks_b)
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


def patterns_by_alphabet(
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


def compute_concepts(
    relation: dict[str, set[str]], *, max_concepts: int = 20_000,
) -> list[FCAConcept]:
    """All formal concepts of a binary relation.

    Every concept intent is an intersection of object rows, so the concept set is the
    meet-closure of the rows (plus the top — the intent of the empty extent). Computing
    it that way is bounded by the number of *actual* concepts, which is small for real
    identifier relations. The previous implementation brute-forced every attribute
    subset — ``2**len(attributes)`` — which is ~2^38 (≈275e9) on the slop corpus and
    pegged a core indefinitely. A ``max_concepts`` backstop keeps a pathological lattice
    (densely overlapping rows) from wedging the linter: such a scope yields no crisp
    sprawl finding anyway, so we skip it rather than spin.
    """
    objects = list(relation.keys())
    rows = {o: frozenset(relation[o]) for o in objects}
    attributes = frozenset().union(*rows.values()) if rows else frozenset()
    if not attributes:
        return []

    def extent(intent: frozenset[str]) -> frozenset[str]:
        return frozenset(o for o in objects if intent <= rows[o])

    def intent(ext: frozenset[str]) -> frozenset[str]:
        if not ext:
            return attributes
        return frozenset.intersection(*(rows[o] for o in ext))

    # Meet-closure of the object rows: seed with every row + the top, then intersect
    # each newly found intent with every row until no new intent appears (fixpoint).
    intents: set[frozenset[str]] = {attributes}
    intents.update(rows.values())
    frontier = list(intents)
    while frontier:
        nxt: list[frozenset[str]] = []
        for i in frontier:
            for r in rows.values():
                x = i & r
                if x not in intents:
                    intents.add(x)
                    nxt.append(x)
                    if len(intents) > max_concepts:
                        return []  # pathological lattice — skip rather than wedge
        frontier = nxt

    concepts = {(e, intent(e)) for e in (extent(i) for i in intents)}
    return [
        FCAConcept(extent=e, intent=i)
        for e, i in sorted(concepts, key=lambda c: (-len(c[1]), -len(c[0])))
    ]


def find_inheritance_pairs(
    relation: dict[str, set[str]],
    min_parent_ops: int = 2,
) -> list[tuple[str, str]]:
    """Pairs ``(parent, child)`` where child's intent ⊃ parent's strictly,
    parent has ≥ ``min_parent_ops`` ops, and no entity sits between them
    in the lattice."""
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


def affix_at_scope(
    items: list[Lexeme],
    scope_path: tuple[str, ...],
    min_alphabet: int,
) -> tuple[list[AffixCluster], list[FCAConcept], list[tuple[str, str, frozenset[str]]]]:
    """Run pattern detection + FCA + inheritance lattice on one scope's items."""
    if len(items) < 2:
        return ([], [], [])

    scope_str, scope_kind = scope_label(scope_path)

    patterns = build_affix_patterns(items, exclude=UNIVERSAL_NOISE)
    clusters = patterns_by_alphabet(patterns, min_alphabet=min_alphabet)
    for c in clusters:
        c.scope = scope_str
        c.scope_kind = scope_kind

    relation: dict[str, set[str]] = {}
    member_files: dict[str, set[str]] = {}
    if clusters:
        primary = max(clusters, key=lambda c: sum(len(p.variants) for p in c.patterns))
        for pattern in primary.patterns:
            stem_no_star = "_".join(t for t in pattern.stem if t != "*")
            for entity, srcs in pattern.variants.items():
                relation.setdefault(entity, set()).add(stem_no_star or "<empty>")
                member_files.setdefault(entity, set()).update(
                    f for _t, f, _l in srcs if f)

    concepts = compute_concepts(relation) if relation else []
    for c in concepts:
        c.scope = scope_str
        c.scope_kind = scope_kind
        c.files = frozenset().union(*(member_files.get(m, set()) for m in c.extent)) \
            if c.extent else frozenset()
    inheritance = [
        (parent, child,
         frozenset(member_files.get(parent, set()) | member_files.get(child, set())))
        for parent, child in (find_inheritance_pairs(relation) if relation else [])
    ]

    return (clusters, concepts, inheritance)


@dataclass
class SprawlData:
    clusters: list[AffixCluster] = field(default_factory=list)
    concepts: list[FCAConcept] = field(default_factory=list)
    inheritance_pairs: list[tuple[str, str, frozenset[str]]] = field(default_factory=list)
    files_searched: int = 0
    functions_analyzed: int = 0


def sprawl_over(
    items: list[Lexeme],
    *,
    min_alphabet: int = 3,
) -> SprawlData:
    """Run the full recursive-namespace sprawl algorithm over a Lexeme list.

    Walks file → package → root, claiming alphabet members at the
    narrowest scope where the pattern coheres. Caller is responsible
    for building the ``items`` list with ``Lexeme.file`` populated as
    a relative path (slash-separated parts inform the namespace tree).
    """
    files_seen: set[str] = set()
    for it in items:
        if it.file:
            files_seen.add(it.file)

    by_prefix: dict[tuple[str, ...], list[Lexeme]] = {(): list(items)}
    for it in items:
        parts = tuple((it.file or "").replace("\\", "/").split("/"))
        for depth in range(1, len(parts) + 1):
            by_prefix.setdefault(parts[:depth], []).append(it)

    paths = sorted(by_prefix.keys(), key=lambda p: -len(p))
    claimed_entities: set[tuple[tuple[str, ...], str]] = set()

    all_clusters: list[AffixCluster] = []
    all_concepts: list[FCAConcept] = []
    all_pairs: list[tuple[str, str, frozenset[str]]] = []
    emitted_alphabets: list[tuple[tuple[str, ...], frozenset[str]]] = []

    for path in paths:
        clusters, concepts, inheritance = affix_at_scope(
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
            for parent, child, pfiles in inheritance:
                if parent in kept_alphabet and child in kept_alphabet:
                    all_pairs.append((parent, child, pfiles))

    return SprawlData(
        clusters=all_clusters,
        concepts=all_concepts,
        inheritance_pairs=all_pairs,
        files_searched=len(files_seen),
        functions_analyzed=len(items),
    )
