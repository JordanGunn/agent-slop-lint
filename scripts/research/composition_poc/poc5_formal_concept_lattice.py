"""PoC 5: Formal Concept Analysis + kernel-language density matrix.

Combines two views:

**Section A — FCA concept lattice.** Builds the binary relation
``language × operation``: language L has an override for operation O
iff a function ``_L_O`` (or stem-permutation thereof) exists. Computes
the formal concepts (closed pairs of (extent, intent)), the Hasse
diagram (immediate-subconcept relations), and explicit inheritance
candidates: when entity A's intent is a strict subset of entity B's
intent, B inherits-from A.

**Section B — Kernel × language density matrix.** Per-kernel, per-
language, which cells have data references (registry entries) and
which have behaviour references (functions tagged with the language).
Surfaces which dimensions are dense (suggesting matrix-shaped
structure) vs sparse (suggesting boundary cases).

Theoretical basis
-----------------
- Wille (1982), "Restructuring Lattice Theory" — original FCA paper.
- Ganter & Wille (1999), Formal Concept Analysis — canonical reference.
- For software engineering applications: Tilley et al., "Formal
  Concept Analysis Applied to Software Engineering" (2005).

Usage
-----
    python poc5_formal_concept_lattice.py FILE [FILE ...]
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

DEF_RE = re.compile(r"^def\s+(\w+)\s*\(", re.MULTILINE)

# Closed alphabet of language tokens. In a productionised version this
# would be auto-discovered from PoC1's clustering output.
LANGUAGE_ALPHABET = {
    "python", "javascript", "typescript", "rust", "go", "java",
    "csharp", "julia", "c", "cpp", "ruby", "js", "ts", "default",
}


def split_identifier(name):
    s = name.strip("_")
    return [t.lower() for t in re.split(r"[_]+", s) if t]


def collect_overrides(paths):
    """Return (relation, behaviour_locations).

    relation: dict[language] → set[operation]
    behaviour_locations: dict[(language, operation)] → list[(file, line)]
    """
    relation = defaultdict(set)
    locations = defaultdict(list)
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in DEF_RE.finditer(text):
            name = m.group(1)
            tokens = split_identifier(name)
            if not tokens:
                continue
            # Find the language token's position
            for i, tok in enumerate(tokens):
                if tok in LANGUAGE_ALPHABET:
                    # Operation = stem with the language removed
                    operation_tokens = tokens[:i] + tokens[i + 1:]
                    if not operation_tokens:
                        continue
                    operation = "_".join(operation_tokens)
                    relation[tok].add(operation)
                    line_no = text[:m.start()].count("\n") + 1
                    locations[(tok, operation)].append((p.name, line_no))
                    break  # first language token wins
    return dict(relation), dict(locations)


def collect_data_references(paths, alphabet):
    """Return dict[(file, language)] → list[line_no] for dict-key data refs."""
    out = defaultdict(list)
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="replace")
        for ln, line in enumerate(text.splitlines(), start=1):
            for lang in alphabet:
                # Look for "lang": at start of line content (dict key)
                pat = rf"['\"]({re.escape(lang)})['\"]:"
                if re.search(pat, line):
                    out[(p.name, lang)].append(ln)
                # c_sharp aliasing
                if lang == "csharp" and re.search(r"['\"]c_sharp['\"]:", line):
                    out[(p.name, "csharp")].append(ln)
    return dict(out)


# ---------------------------------------------------------------------------
# Formal concept analysis
# ---------------------------------------------------------------------------


def all_concepts(relation):
    """Compute all formal concepts of a binary relation.

    Brute-force over the powerset of attributes (operations); fine for
    small N. Returns list of (extent, intent) tuples, with extent and
    intent as frozensets.
    """
    objects = list(relation.keys())                     # languages
    attributes = sorted({a for s in relation.values() for a in s})  # operations

    def extent_of(intent):
        """Languages that have every operation in `intent`."""
        if not intent:
            return frozenset(objects)
        return frozenset(o for o in objects if intent.issubset(relation[o]))

    def intent_of(extent):
        """Operations every language in `extent` has."""
        if not extent:
            return frozenset(attributes)
        sets = [relation[o] for o in extent]
        return frozenset.intersection(*[frozenset(s) for s in sets])

    concepts = set()
    # Enumerate the powerset of attributes.
    for r in range(len(attributes) + 1):
        for combo in combinations(attributes, r):
            ext = extent_of(frozenset(combo))
            inn = intent_of(ext)
            concepts.add((ext, inn))
    # Also include each object's row as a concept seed
    for o in objects:
        ext = frozenset(o2 for o2 in objects if relation[o].issubset(relation[o2]))
        inn = intent_of(ext)
        concepts.add((ext, inn))

    return sorted(concepts, key=lambda c: (-len(c[1]), -len(c[0])))


def compute_hasse_edges(concepts):
    """Return list of (parent_idx, child_idx) for the Hasse diagram.

    Concept C1 is parent of C2 iff C2.intent ⊃ C1.intent and there's
    no C3 strictly between them.
    """
    n = len(concepts)
    edges = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            ci, cj = concepts[i], concepts[j]
            if not (cj[1] > ci[1]):  # cj is more specific (larger intent)
                continue
            # Check no intermediate
            intermediate = False
            for k in range(n):
                if k in (i, j):
                    continue
                ck = concepts[k]
                if ci[1] < ck[1] < cj[1]:
                    intermediate = True
                    break
            if not intermediate:
                edges.append((i, j))
    return edges


def find_inheritance_pairs(relation, min_parent_ops: int = 2):
    """Find (parent, child) language pairs where child's intent ⊃ parent's.

    Filters out trivial parents (single-operation entities) to reduce
    noise from degenerate subset relations. ``min_parent_ops`` defaults
    to 2: an inheritance candidate must have at least two operations
    inherited; otherwise the relation is too weak to be structurally
    meaningful.
    """
    out = []
    for a in relation:
        if len(relation[a]) < min_parent_ops:
            continue
        for b in relation:
            if a == b:
                continue
            if relation[a] and relation[a] < relation[b]:
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
# Reporting
# ---------------------------------------------------------------------------


def render_relation_table(relation, attributes):
    lines = ["| Language | " + " | ".join(f"`{a}`" for a in attributes) + " |"]
    lines.append("|---|" + "---|" * len(attributes))
    for lang in sorted(relation):
        cells = [("✓" if a in relation[lang] else "") for a in attributes]
        lines.append(f"| `{lang}` | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_concepts(concepts):
    lines = []
    for idx, (ext, inn) in enumerate(concepts):
        if not ext or not inn:
            # Skip top (all langs, no ops) and bottom (no langs, all ops) trivial concepts
            kind = "TOP" if not inn else "BOTTOM"
            lines.append(f"### Concept {idx}: {kind}")
            lines.append(f"- entities: {{{', '.join(f'`{l}`' for l in sorted(ext))}}}")
            lines.append(f"- operations: {{{', '.join(f'`{a}`' for a in sorted(inn))}}}")
            lines.append("")
            continue
        ext_s = ", ".join(f"`{l}`" for l in sorted(ext))
        inn_s = ", ".join(f"`{a}`" for a in sorted(inn))
        lines.append(f"### Concept {idx}: {{{ext_s}}} × {{{inn_s}}}")
        lines.append(f"- {len(ext)} entit{'ies' if len(ext) != 1 else 'y'}: "
                     f"{ext_s}")
        lines.append(f"- {len(inn)} operation{'s' if len(inn) != 1 else ''}: "
                     f"{inn_s}")
        if len(ext) >= 2 and len(inn) >= 2:
            lines.append(f"- **Class candidate**: a `Language` (or named "
                         f"after the entity group) class providing "
                         f"these operations as methods. "
                         f"{len(ext)} entities would inherit from / "
                         f"instantiate this class.")
        lines.append("")
    return "\n".join(lines)


def render_inheritance(pairs, locations):
    lines = []
    if not pairs:
        lines.append("_No strict-subset inheritance relations detected._")
        return "\n".join(lines)
    for a, b in pairs:
        lines.append(f"- `{b}` inherits from `{a}`. `{b}` overrides "
                     f"every operation `{a}` overrides, plus "
                     f"additional operations.")
    return "\n".join(lines)


def render_kernel_matrix(paths, alphabet, behaviour_relation, data_refs):
    """Per-kernel × per-language density.

    For each (kernel-file, language) cell:
      - data: count of dict-key occurrences in that file for that language
      - behaviour: count of functions tagged `_<lang>_*` in that file
    """
    files = sorted({p.name for p in paths})
    langs = sorted({l for l in behaviour_relation} | {l for _, l in data_refs})

    lines = ["", "| Language \\ File | " + " | ".join(files) + " | total |"]
    lines.append("|---|" + "---|" * (len(files) + 1))
    for lang in langs:
        cells = []
        total_d = total_b = 0
        for f in files:
            d = len(data_refs.get((f, lang), []))
            # Behaviour count for this (lang, file): scan paths
            b = 0
            for p in paths:
                if p.name != f:
                    continue
                text = p.read_text(encoding="utf-8", errors="replace")
                for m in DEF_RE.finditer(text):
                    toks = split_identifier(m.group(1))
                    if lang in toks:
                        b += 1
            total_d += d
            total_b += b
            if d == 0 and b == 0:
                cells.append("·")
            else:
                cells.append(f"d={d} b={b}")
        cells.append(f"d={total_d} b={total_b}")
        lines.append(f"| `{lang}` | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def report(paths):
    relation, locations = collect_overrides(paths)
    data_refs = collect_data_references(paths, LANGUAGE_ALPHABET)

    out = ["# composition.formal_concept_lattice — structural decomposition",
           "",
           "This report combines two views over the codebase:",
           "",
           "1. **Section A** — formal concept analysis of the binary "
           "relation between candidate entities (languages) and "
           "candidate operations (the stem patterns). The lattice's "
           "concepts are the natural class groupings; the Hasse "
           "diagram is the inheritance graph.",
           "2. **Section B** — kernel × language density matrix, "
           "showing where data and behaviour live across the (kernel, "
           "language) plane. A dense, uniform matrix indicates a "
           "two-dimensional structure that the current flat-file "
           "layout doesn't express.",
           ""]

    # Section A — FCA
    out += ["## Section A — Formal Concept Lattice", ""]

    if not relation:
        out.append("_No language-tagged overrides detected; FCA produced no "
                   "lattice._")
    else:
        attributes = sorted({a for s in relation.values() for a in s})
        out.append("### A.1 Binary relation: language × operation")
        out.append("")
        out.append("Each ✓ marks a language having a per-language override "
                   "for the given operation. The relation is the input to "
                   "the lattice computation.")
        out.append("")
        out.append(render_relation_table(relation, attributes))
        out.append("")

        out.append(f"**Entities (languages)**: {len(relation)}")
        out.append(f"**Attributes (operations)**: {len(attributes)}")
        out.append(f"**Cells filled**: {sum(len(v) for v in relation.values())}"
                   f" / {len(relation) * len(attributes)}")
        out.append("")

        concepts = all_concepts(relation)
        out.append(f"### A.2 Formal concepts ({len(concepts)} total)")
        out.append("")
        out.append("Each concept (E, I) is a pair where E is the maximal "
                   "set of entities that share all operations in I, and I "
                   "is the maximal set of operations shared by all entities "
                   "in E. A concept with |E| ≥ 2 entities AND |I| ≥ 2 "
                   "operations is a candidate **class**: the I operations "
                   "would be methods on the class; the E entities would be "
                   "instances or subclasses.")
        out.append("")
        out.append(render_concepts(concepts))

        # Hasse — render edges as a list
        edges = compute_hasse_edges(concepts)
        if edges:
            out.append("### A.3 Hasse diagram (immediate-subconcept edges)")
            out.append("")
            out.append("Each edge `parent → child` means child's intent "
                       "(operations) is an immediate strict superset of "
                       "parent's. This is the **inheritance graph**: a "
                       "child concept's class would extend its parent's.")
            out.append("")
            for parent_idx, child_idx in edges:
                p_ext = ", ".join(f"`{l}`" for l in sorted(concepts[parent_idx][0])) or "_(empty)_"
                p_inn = ", ".join(f"`{a}`" for a in sorted(concepts[parent_idx][1])) or "_(empty)_"
                c_ext = ", ".join(f"`{l}`" for l in sorted(concepts[child_idx][0])) or "_(empty)_"
                c_inn = ", ".join(f"`{a}`" for a in sorted(concepts[child_idx][1])) or "_(empty)_"
                out.append(f"- C{parent_idx} ({{ {p_inn} }}) → C{child_idx} ({{ {c_inn} }})  "
                           f"[entities {{{c_ext}}} extend entities "
                           f"{{{p_ext}}}]")
            out.append("")

        # Inheritance pairs (entity-level, simpler view)
        inh = find_inheritance_pairs(relation)
        out.append("### A.4 Direct inheritance candidates (entity-level)")
        out.append("")
        out.append("Pairs of entities (parent, child) where the child's "
                   "operation set is a strict superset of the parent's. "
                   "These are the most actionable inheritance candidates: "
                   "`class Child(Parent)` is structurally justified.")
        out.append("")
        out.append(render_inheritance(inh, locations))
        out.append("")

    # Section B — kernel matrix
    out += ["", "## Section B — Kernel × language density matrix", ""]
    out.append("Each cell shows `d=N b=M` where d is data references "
               "(registry / config dict-key occurrences) and b is "
               "behaviour references (functions tagged with the language). "
               "A dot (·) means the cell is empty.")
    out.append("")
    out.append("A dense, uniform matrix indicates a two-axis structure "
               "(kernel × language) currently flattened across files. "
               "The natural decomposition separates the two axes: per-"
               "language behaviour and data become a `Language` entity; "
               "per-kernel logic stays with the kernel.")
    out.append("")
    out.append(render_kernel_matrix(paths, LANGUAGE_ALPHABET, relation, data_refs))
    out.append("")

    # Headline diagnosis
    out += ["", "## Section C — Diagnosis", ""]
    if relation:
        attributes = sorted({a for s in relation.values() for a in s})
        out.append(f"The codebase has a {len(relation)}-entity × "
                   f"{len(attributes)}-operation relation that forms a "
                   f"non-trivial concept lattice. The lattice contains "
                   f"{sum(1 for c in concepts if len(c[0]) >= 2 and len(c[1]) >= 2)} "
                   f"candidate classes (concepts with multiple entities "
                   f"sharing multiple operations) and "
                   f"{len(inh)} direct inheritance edges.")
        out.append("")
        out.append("**Recommended decomposition**: a `Language` "
                   "abstraction whose subclasses correspond to the "
                   "lattice's join-irreducible concepts. The inheritance "
                   "edges in section A.4 give the class hierarchy directly. "
                   "Kernel-specific data (decision nodes, operator types, "
                   "switch semantics) stays with the kernels — those "
                   "fields are not part of the language axis.")

    return "\n".join(out)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)
    paths = [Path(p) for p in argv[1:]]
    print(report(paths))


if __name__ == "__main__":
    main(sys.argv)
