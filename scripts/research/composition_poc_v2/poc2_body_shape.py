"""PoC v2.2 — Body-shape signatures (Type-2 clone-style).

For each function in a cluster, compute a normalized AST signature:
the sequence of node types in DFS order, with leaf identifiers /
literals / punctuation collapsed. Cluster cohesion is then scored
by pairwise signature similarity.

A cluster with high body-shape cohesion is a real "do the same
thing with parametric variation" family — exactly the Type-2 clone
case where extracting a base class or strategy table is justified.
A cluster with low cohesion is a bag of unrelated functions that
happen to share an input.

Theoretical grounding
---------------------
- Roy, Cordy & Koschke (2009) "Comparison and evaluation of code
  clone detection techniques and tools" — survey of clone-detection
  signal types (Type 1: identical; Type 2: identical structure with
  different identifiers; Type 3+: structural variation).
- Baxter et al. (1998) "Clone Detection Using Abstract Syntax
  Trees" — AST-based detection foundation.
- slop's own `structural.duplication` rule already implements
  Type-2 detection at file scope; this PoC reuses the primitive
  at within-cluster scope.

Usage
-----
    cd src
    uv run python ../scripts/research/composition_poc_v2/poc2_body_shape.py cli/slop
"""
from __future__ import annotations

import sys
from pathlib import Path

from slop._lexical._naming import enumerate_functions
from slop._structural.composition import first_parameter_drift_kernel


# Node types we DON'T emit in the signature (noise-suppressing).
_LEAF_OR_NOISE = frozenset({
    "identifier", "integer", "float", "string", "string_content",
    "true", "false", "none", "comment",
    ":", ",", "(", ")", "[", "]", "{", "}", ".",
    "=", "+", "-", "*", "/", "%", "<", ">", "==", "!=",
    "string_start", "string_end",
})


def _signature(node, content: bytes) -> list[str]:
    """DFS over node, emitting structural node types only."""
    sig: list[str] = []

    def walk(n):
        t = n.type
        if t not in _LEAF_OR_NOISE:
            sig.append(t)
        for child in n.children:
            walk(child)

    walk(node)
    return sig


def _ngrams(seq: list[str], n: int = 3) -> set[tuple[str, ...]]:
    if len(seq) < n:
        return {tuple(seq)} if seq else set()
    return {tuple(seq[i:i + n]) for i in range(len(seq) - n + 1)}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main(root: str) -> None:
    print("# PoC v2.2 — Body-shape signatures")
    print()
    # Pull clusters
    drift_result = first_parameter_drift_kernel(Path(root), languages=["python"])
    # Index function bodies for sig lookup
    bodies: dict[tuple[str, str], list[str]] = {}  # (file, name) -> signature
    for ctx in enumerate_functions(Path(root), languages=["python"]):
        if ctx.body_node is None:
            continue
        bodies[(ctx.file, ctx.name)] = _signature(ctx.body_node, ctx.content)

    print(f"Root: `{root}`  |  Indexed {len(bodies)} function bodies  |  Clusters: {len(drift_result.clusters)}")
    print()
    print("| Cluster | Scope | Members | Mean pairwise Jaccard (3-gram) | Verdict |")
    print("|---|---|---|---|---|")

    detail: list[tuple] = []
    for c in drift_result.clusters:
        if c.verdict != "strong":
            continue
        sigs = []
        for name, file, _ in c.members:
            sig = bodies.get((file, name))
            if sig is not None:
                sigs.append((name, file, _ngrams(sig, 3)))
        if len(sigs) < 2:
            continue
        # Pairwise Jaccard
        scores = []
        for i in range(len(sigs)):
            for j in range(i + 1, len(sigs)):
                scores.append(_jaccard(sigs[i][2], sigs[j][2]))
        mean = sum(scores) / len(scores) if scores else 0.0
        verdict = (
            "**high cohesion** (clone family)" if mean >= 0.7
            else "moderate" if mean >= 0.4
            else "low (heterogeneous)"
        )
        print(f"| `{c.parameter_name}` | `{c.scope}` | {len(sigs)} | {mean:.2f} | {verdict} |")
        detail.append((c, sigs, mean))

    print()
    print("## Per-cluster detail")
    print()
    for c, sigs, mean in detail:
        print(f"### `{c.parameter_name}` in `{c.scope}` (mean Jaccard {mean:.2f})")
        print()
        for name, file, ngrams in sigs:
            print(f"- `{name}` ({file}): {len(ngrams)} 3-grams")
        # Show shared 3-grams across all members
        if sigs:
            shared = sigs[0][2].copy()
            for _, _, ngrams in sigs[1:]:
                shared &= ngrams
            if shared:
                print(f"- Shared 3-grams (in all members): {len(shared)}")
                for s in list(shared)[:6]:
                    print(f"    - `{' → '.join(s)}`")
        print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
