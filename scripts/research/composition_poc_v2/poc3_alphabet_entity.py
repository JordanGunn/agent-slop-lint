"""PoC v2.3 — Closed-alphabet entity recognition.

When the same closed alphabet (set of token values) appears across
many stems, files, and module-level dict literals, the alphabet
itself is a candidate **entity type**. The classic case for slop:
the language alphabet `{python, javascript, java, c, cpp, ruby,
...}` appears as keys in `_FUNCTION_NODES`, `_LANG_GLOBS`,
`_CLASS_NODES`, and as varying tokens in many `_<lang>_*` helpers.
A `Language` class with attributes (name, file_extensions,
function_node_types, OOP-flag) would consolidate the dispatched
behaviour scattered across the codebase.

This PoC scores each detected closed alphabet by:
1. Number of distinct stems where it varies
2. Number of files that mention any alphabet member
3. Number of module-level dict literals with alphabet members as keys

Theoretical grounding
---------------------
- Wille (1982) FCA — operates on entity × operation relations;
  this PoC asks instead "what makes an alphabet entity-worthy"
  rather than "what operations does an entity have."
- Tonella's FCA-of-execution-traces work on aspect mining is the
  closest published precedent for "treat the alphabet itself as
  the discovery target."
- Otherwise novel — flagged as such.

Usage
-----
    cd src
    uv run python ../scripts/research/composition_poc_v2/poc3_alphabet_entity.py cli/slop
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from slop._lexical._naming import enumerate_functions
from slop._structural.composition import (
    _build_affix_patterns,
    _cluster_patterns_by_alphabet,
    _split,
)
from slop._fs.find import find_kernel
from slop._ast.treesitter import detect_language, load_language


def _module_dicts_with_keys(root: Path) -> dict[str, list[tuple[frozenset[str], int]]]:
    """Walk Python files; for each module-level assignment to a
    dict literal, record the keys. Returns ``{file: [(keys, line)]}``."""
    out: dict[str, list[tuple[frozenset[str], int]]] = {}
    find_result = find_kernel(root=root, globs=["**/*.py"])
    files = [root / e.path for e in find_result.entries if e.type == "file"]
    for fp in files:
        lang = detect_language(fp)
        if lang != "python":
            continue
        tree_lang = load_language(lang)
        if tree_lang is None:
            continue
        try:
            import tree_sitter
            content = fp.read_bytes()
            try:
                parser = tree_sitter.Parser(tree_lang)
                tree = parser.parse(content)
            except TypeError:
                parser = tree_sitter.Parser()
                parser.language = tree_lang
                tree = parser.parse(content)
        except Exception:
            continue
        try:
            rel = str(fp.relative_to(root))
        except ValueError:
            rel = str(fp)
        # Top-level assignments: in Python TS, they're wrapped in
        # ``expression_statement``. Walk module children → expression
        # statements → assignment.
        for ms in tree.root_node.children:
            assignment_node = None
            if ms.type == "assignment":
                assignment_node = ms
            elif ms.type == "expression_statement":
                for sub in ms.children:
                    if sub.type == "assignment":
                        assignment_node = sub
                        break
            if assignment_node is None:
                continue
            right = assignment_node.child_by_field_name("right")
            if right is None or right.type != "dictionary":
                continue
            keys: set[str] = set()
            for pair in right.children:
                if pair.type != "pair":
                    continue
                k = pair.child_by_field_name("key")
                if k is None:
                    continue
                if k.type == "string":
                    text = content[k.start_byte:k.end_byte].decode(
                        "utf-8", errors="replace",
                    ).strip("'\"")
                    keys.add(text.lower())
                elif k.type == "identifier":
                    keys.add(content[k.start_byte:k.end_byte].decode(
                        "utf-8", errors="replace",
                    ).lower())
            if keys:
                out.setdefault(rel, []).append(
                    (frozenset(keys), assignment_node.start_point[0] + 1),
                )
    return out


def main(root: str) -> None:
    print("# PoC v2.3 — Closed-alphabet entity recognition")
    print()
    rp = Path(root)

    # Collect all functions
    items: list[tuple[str, str, int, list[str]]] = []
    for ctx in enumerate_functions(rp, languages=["python"]):
        if ctx.name.startswith("<") or len(ctx.name) < 2:
            continue
        items.append((ctx.name, ctx.file, ctx.line, _split(ctx.name)))

    # Find affix patterns + closed alphabets
    patterns = _build_affix_patterns(items)
    clusters = _cluster_patterns_by_alphabet(patterns, min_alphabet=3)
    module_dicts = _module_dicts_with_keys(rp)

    print(f"Root: `{root}`  |  Functions: {len(items)}  |  Clusters: {len(clusters)}")
    print(f"Module-level dicts found: {sum(len(v) for v in module_dicts.values())}")
    print()
    print("## Closed alphabets ranked by entity-ness score")
    print()
    print("| Alphabet | Members | # Stems | # Files | # Dict-key matches | Score |")
    print("|---|---|---|---|---|---|")

    rows: list[tuple] = []
    for cluster in clusters:
        alpha = cluster.alphabet
        n_stems = len(cluster.patterns)
        files = set()
        for pattern in cluster.patterns:
            for entity, members in pattern.variants.items():
                for _, file, _ in members:
                    files.add(file)
        n_files = len(files)
        # Count module-level dicts whose keys overlap the alphabet by ≥ 2
        dict_matches = 0
        for f, dicts in module_dicts.items():
            for keys, _line in dicts:
                if len(keys & alpha) >= 2:
                    dict_matches += 1
        score = n_stems * 2 + n_files + dict_matches * 3

        members_short = ", ".join(sorted(alpha))[:60]
        if len(", ".join(sorted(alpha))) > 60:
            members_short += "…"
        rows.append((score, members_short, len(alpha), n_stems, n_files, dict_matches))

    rows.sort(reverse=True)
    for score, members, n, n_stems, n_files, dict_matches in rows:
        print(f"| {{{members}}} | {n} | {n_stems} | {n_files} | {dict_matches} | **{score}** |")

    print()
    print("## Top alphabets — detail")
    print()
    for score, members, n, n_stems, n_files, dict_matches in rows[:5]:
        print(f"### Alphabet `{members}` (score {score})")
        print(f"- {n} members, {n_stems} stems, {n_files} files, {dict_matches} module-dict matches")
        print()
        # Show which stems
        for cluster in clusters:
            this_alpha_str = ", ".join(sorted(cluster.alphabet))[:60]
            if this_alpha_str.startswith(members.rstrip("…").rstrip()[:30]):
                for pattern in cluster.patterns[:5]:
                    stem_repr = "_".join(pattern.stem)
                    print(f"  - stem `{stem_repr}`: variants {sorted(pattern.variants.keys())[:8]}")
                break
        print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
