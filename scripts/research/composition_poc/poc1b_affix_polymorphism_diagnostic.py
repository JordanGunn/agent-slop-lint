"""PoC 1b: Affix polymorphism detection — diagnostic output framing.

Same algorithm as poc1, but reports candidates as **missing namespace**
diagnoses rather than as raw "shared affix" patterns.

The framing change is the experiment: does naming the diagnosis
("entity X is the missing namespace; it has data here and behaviour
there") produce different downstream redesign decisions than reporting
the symptom ("these N identifiers share a stem")?
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

DEF_RE = re.compile(r"^def\s+(\w+)\s*\(", re.MULTILINE)
CAMEL_LU = re.compile(r"([a-z])([A-Z])")
CAMEL_UU = re.compile(r"([A-Z]+)([A-Z][a-z])")


def split_identifier(name: str) -> list[str]:
    s = name.strip("_")
    s = CAMEL_LU.sub(r"\1_\2", s)
    s = CAMEL_UU.sub(r"\1_\2", s)
    return [t.lower() for t in re.split(r"[_]+", s) if t]


def token_edit_distance(a, b):
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return (max(la, lb), None, None, None)
    if la == lb:
        diffs = [(i, a[i], b[i]) for i in range(la) if a[i] != b[i]]
        if len(diffs) == 1:
            i, ta, tb = diffs[0]
            return (1, i, ta, tb)
        return (len(diffs), None, None, None)
    longer, shorter = (a, b) if la > lb else (b, a)
    for i in range(len(longer)):
        if longer[:i] + longer[i + 1:] == shorter:
            return (1, i, longer[i], None)
    return (2, None, None, None)


def collect_definitions(paths):
    defs = []
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in DEF_RE.finditer(text):
            name = m.group(1)
            defs.append((name, p, split_identifier(name)))
    return defs


def find_affix_groups(defs):
    groups = defaultdict(lambda: defaultdict(list))
    for i, (na, pa, ta) in enumerate(defs):
        for nb, pb, tb in defs[i + 1:]:
            d, pos, x, y = token_edit_distance(ta, tb)
            if d != 1 or pos is None or len(ta) != len(tb):
                continue
            stem = tuple(ta[:pos] + ["*"] + ta[pos + 1:])
            groups[(stem, pos)][x].append((na, pa))
            groups[(stem, pos)][y].append((nb, pb))
    return groups


def aggregate_by_alphabet(groups, min_alphabet=3):
    """Group patterns by their type alphabet.

    Two patterns sharing >=2 alphabet tokens belong to the same
    underlying entity. e.g., ``*_name_extractor`` over {c, cpp, julia,
    ruby} and ``*_is_function_node`` over {julia, ruby} share an
    underlying ``language`` entity.
    """
    raw_patterns = []
    for (stem, pos), variants in groups.items():
        if len(variants) >= min_alphabet:
            raw_patterns.append((stem, pos, variants))

    if not raw_patterns:
        return []

    # Cluster patterns by alphabet overlap (transitive)
    parent = list(range(len(raw_patterns)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(x, y):
        parent[find(x)] = find(y)

    for i in range(len(raw_patterns)):
        ai = set(raw_patterns[i][2].keys())
        for j in range(i + 1, len(raw_patterns)):
            aj = set(raw_patterns[j][2].keys())
            if len(ai & aj) >= 2:
                union(i, j)

    clusters = defaultdict(list)
    for i, p in enumerate(raw_patterns):
        clusters[find(i)].append(p)

    return list(clusters.values())


def stem_str(stem):
    return "_".join(stem)


def alphabet_label(alpha: set[str]) -> str:
    """Best-guess label for an entity given its alphabet.

    Heuristic: if alphabet matches known buckets, use a known name.
    Otherwise the entity is unnamed; let the reader infer.
    """
    LANGUAGE_TOKENS = {"python", "julia", "c", "cpp", "ruby", "java",
                       "csharp", "ts", "js", "go", "rust", "default", "no"}
    if alpha & LANGUAGE_TOKENS == alpha:
        return "language"
    OPERATION_TOKENS = {"cbo", "dit", "noc", "wmc", "halstead",
                        "ccx", "cog", "npath"}
    if alpha & OPERATION_TOKENS == alpha:
        return "metric"
    return "<unnamed>"


def report(clusters):
    lines = ["# composition.affix_polymorphism — missing-namespace candidates",
             ""]
    if not clusters:
        lines.append("_No affix-polymorphism candidates detected._")
        return "\n".join(lines)

    # Sort clusters by total membership (descending)
    def total_members(cluster):
        seen = set()
        for stem, pos, variants in cluster:
            for tok, members in variants.items():
                for name, path in members:
                    seen.add((name, str(path)))
        return len(seen)
    clusters.sort(key=lambda c: -total_members(c))

    for idx, cluster in enumerate(clusters, start=1):
        # Aggregate the cluster's alphabet and operations
        alpha = set()
        operations = []
        for stem, pos, variants in cluster:
            alpha |= set(variants.keys())
            operations.append((stem, pos, variants))

        entity = alphabet_label(alpha)

        lines.append(f"## Candidate {idx}: missing namespace `{entity}`")
        lines.append("")
        lines.append(f"**Diagnosis**: an entity named `{entity}` is "
                     f"implicit but unnamed in the codebase. The same "
                     f"alphabet of values appears as a varying token "
                     f"across multiple operations, with no shared "
                     f"abstraction binding the operations to the "
                     f"entity.")
        lines.append("")
        lines.append(f"**Entity alphabet** ({len(alpha)} values): "
                     + ", ".join(f"`{t}`" for t in sorted(alpha)))
        lines.append("")
        lines.append(f"**Operations sharing this alphabet** ({len(operations)}):")
        lines.append("")
        for stem, pos, variants in operations:
            display = stem_str(stem)
            file_count = len({str(p) for members in variants.values() for _, p in members})
            total = sum(len(v) for v in variants.values())
            lines.append(f"- `{display}` — {len(variants)} entity values, "
                         f"{total} occurrences across {file_count} file(s)")
        lines.append("")
        lines.append("**Compositional mechanisms that would make the "
                     f"entity explicit**:")
        lines.append("")
        lines.append(f"- A `{entity.capitalize()}` class / trait / "
                     "interface bundling per-entity data and behaviour. "
                     "Each value of the alphabet becomes an instance or "
                     "subclass; each operation becomes a method.")
        lines.append(f"- A `{entity.capitalize()}` registry where each "
                     "entity value maps to a record carrying its data "
                     "and method references.")
        lines.append(f"- A `{entity}/` subpackage with one module per "
                     "entity value, each implementing the operation "
                     "set.")
        lines.append("")
        lines.append("**Per-operation breakdown**:")
        lines.append("")
        lines.append("| Operation | Entity value | Identifier | File |")
        lines.append("|---|---|---|---|")
        for stem, pos, variants in operations:
            display = stem_str(stem)
            for tok in sorted(variants.keys()):
                for name, path in sorted({(n, p.name) for n, p in variants[tok]}):
                    lines.append(f"| `{display}` | `{tok}` | `{name}` | {path} |")
        lines.append("")

    return "\n".join(lines)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)
    paths = [Path(p) for p in argv[1:]]
    defs = collect_definitions(paths)
    groups = find_affix_groups(defs)
    clusters = aggregate_by_alphabet(groups, min_alphabet=3)
    print(report(clusters))


if __name__ == "__main__":
    main(sys.argv)
