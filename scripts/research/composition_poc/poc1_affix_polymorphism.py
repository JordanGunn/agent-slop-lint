"""PoC 1: Token-Levenshtein affix-polymorphism detection.

Algorithm
---------
1. Parse every top-level ``def`` line across the target files.
2. Tokenize each function name (split on underscore + CamelCase).
3. For every pair of names, compute Levenshtein distance over the token
   sequences (NOT character sequences). Distance 1 = single token swap,
   insert, or delete.
4. Group pairs by ``(non-varying-tokens, swap-position)``.
5. For each group, collect the set of varying tokens — call it the
   *type alphabet*.
6. Flag groups where ``|type alphabet| >= 3``: these are the affix
   polymorphism candidates.

Theoretical basis
-----------------
- Caprile & Tonella (2000), "Restructuring program identifier names":
  identifier-pattern analysis as a refactoring trigger.
- Harris (1955), morpheme-boundary detection via successor frequency.
- MDL principle: a uniform stem + variable affix is a more compact
  description than N independent strings, so the decomposition is real.

Usage
-----
    python poc1_affix_polymorphism.py FILE [FILE ...]
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
    """Snake_case + CamelCase tokenizer."""
    s = name.strip("_")
    s = CAMEL_LU.sub(r"\1_\2", s)
    s = CAMEL_UU.sub(r"\1_\2", s)
    return [t.lower() for t in re.split(r"[_]+", s) if t]


def token_edit_distance(a: list[str], b: list[str]) -> tuple[int, int | None, str | None, str | None]:
    """Token-level Levenshtein. Returns (distance, swap_pos, a_tok, b_tok).

    ``swap_pos`` and the two tokens are non-None only when distance == 1
    AND the edit is a substitution (not insert/delete).
    """
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        # Quick reject — distance > 1
        return (max(la, lb), None, None, None)

    if la == lb:
        diffs = [(i, a[i], b[i]) for i in range(la) if a[i] != b[i]]
        if len(diffs) == 1:
            i, ta, tb = diffs[0]
            return (1, i, ta, tb)
        return (len(diffs), None, None, None)

    # |la - lb| == 1 → insert / delete. Find position.
    longer, shorter = (a, b) if la > lb else (b, a)
    for i in range(len(longer)):
        # Try removing longer[i] and check equality
        candidate = longer[:i] + longer[i + 1:]
        if candidate == shorter:
            return (1, i, longer[i], None)
    return (2, None, None, None)


def collect_definitions(paths: list[Path]) -> list[tuple[str, Path, list[str]]]:
    """Return [(raw_name, source_path, tokens), ...]."""
    defs: list[tuple[str, Path, list[str]]] = []
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in DEF_RE.finditer(text):
            name = m.group(1)
            defs.append((name, p, split_identifier(name)))
    return defs


def find_affix_groups(defs):
    """Group identifiers sharing (non-varying tokens, swap position).

    Returns dict: ``(stem_tuple, swap_pos) → {varying_token: [(name, path)]}``.
    """
    groups: dict[tuple[tuple[str, ...], int], dict[str, list[tuple[str, Path]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for i, (name_a, path_a, toks_a) in enumerate(defs):
        for name_b, path_b, toks_b in defs[i + 1:]:
            dist, pos, ta, tb = token_edit_distance(toks_a, toks_b)
            if dist != 1 or pos is None:
                continue
            # Build the stem = tokens minus the variable position
            if len(toks_a) == len(toks_b):
                stem_tuple = tuple(toks_a[:pos] + ["*"] + toks_a[pos + 1:])
                groups[(stem_tuple, pos)][ta].append((name_a, path_a))
                groups[(stem_tuple, pos)][tb].append((name_b, path_b))
            else:
                # Insert/delete edit — record both
                longer = toks_a if len(toks_a) > len(toks_b) else toks_b
                shorter = toks_b if len(toks_a) > len(toks_b) else toks_a
                stem_tuple = tuple(shorter[:pos] + ["?"] + shorter[pos:])
                inserted = longer[pos]
                groups[(stem_tuple, pos)][inserted].append(
                    (name_a if longer is toks_a else name_b,
                     path_a if longer is toks_a else path_b)
                )
                groups[(stem_tuple, pos)]["<empty>"].append(
                    (name_b if longer is toks_a else name_a,
                     path_b if longer is toks_a else path_a)
                )
    return groups


def report(groups, min_alphabet: int = 3) -> str:
    """Render groups whose varying-token alphabet has at least ``min_alphabet`` distinct values."""
    lines: list[str] = []
    candidates = []
    for (stem, pos), variants in groups.items():
        if len(variants) >= min_alphabet:
            total_members = sum(len(v) for v in variants.values())
            candidates.append((total_members, stem, pos, variants))

    candidates.sort(key=lambda x: -x[0])

    lines.append("# PoC 1 — Token-Levenshtein affix-polymorphism candidates\n")
    if not candidates:
        lines.append("_No affix-polymorphism candidates found._\n")
        return "\n".join(lines)

    for total, stem, pos, variants in candidates:
        # Render the stem with `*` highlighting the varying position
        stem_disp = "_".join(stem) if all(t for t in stem) else " ".join(stem)
        lines.append(f"## Pattern: `{stem_disp}` (varying position {pos})\n")
        lines.append(f"**Type alphabet** ({len(variants)} values): "
                     + ", ".join(f"`{t}`" for t in sorted(variants.keys())))
        lines.append(f"**Total members**: {total}")
        lines.append("")
        lines.append("| Varying token | Identifiers |")
        lines.append("|---|---|")
        for tok in sorted(variants.keys()):
            members = sorted({(name, str(p.name)) for name, p in variants[tok]})
            mlist = ", ".join(f"`{n}` ({f})" for n, f in members)
            lines.append(f"| `{tok}` | {mlist} |")
        lines.append("")

    return "\n".join(lines)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)
    paths = [Path(p) for p in argv[1:]]
    defs = collect_definitions(paths)
    groups = find_affix_groups(defs)
    print(report(groups, min_alphabet=3))


if __name__ == "__main__":
    main(sys.argv)
