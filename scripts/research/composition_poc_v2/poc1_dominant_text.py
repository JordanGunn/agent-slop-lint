"""PoC v2.1 — Dominant-text labeling of first-parameter clusters.

For each first-parameter cluster, extract bag-of-tokens from the
member function names (snake/Camel split + lowercase). Find the modal
tokens. Identify the **varying alphabet** (tokens that change between
members) versus the **shared stem** (tokens common to most members).

Output: per-cluster summary that labels the cluster by what's
dominant in its names — without imposing pattern-language vocabulary.

Theoretical grounding
---------------------
- Caprile & Tonella (2000) "Restructuring program identifiers based
  on word usage and stop-word filtering." Token-pattern analysis
  predates this work; we apply the same primitive at a finer scope
  (within an already-clustered group).
- Standard TF / bag-of-tokens primitives from IR.

Usage
-----
    cd src
    uv run python ../scripts/research/composition_poc_v2/poc1_dominant_text.py cli/slop
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from slop._lexical.identifier_tokens import split_identifier
from slop._structural.composition import first_parameter_drift_kernel


def label_cluster(member_names: list[str]) -> dict:
    """Return a structured label for a cluster based on dominant text."""
    tokens_per_name = [
        [t.lower() for t in split_identifier(n)] for n in member_names
    ]
    flat = [t for ts in tokens_per_name for t in ts]
    freq = Counter(flat)
    n = len(member_names)

    # Tokens shared by ≥ 60% of names = "shared stem"
    shared_stem = sorted(
        t for t, c in freq.items() if c / n >= 0.6
    )
    # Tokens that appear once-per-name exactly across members = "varying alphabet"
    # (each member contributes a unique token that's also a hapax in the cluster)
    varying = sorted({
        ts[-1] for ts in tokens_per_name
        if ts and freq[ts[-1]] == 1
    })
    # Modal token (most frequent overall)
    modal = freq.most_common(1)[0] if freq else (None, 0)

    return {
        "n_members": n,
        "modal_token": modal[0],
        "modal_freq": modal[1],
        "shared_stem": shared_stem,
        "varying_alphabet": varying,
        "freq": dict(freq.most_common(8)),
    }


def main(root: str) -> None:
    result = first_parameter_drift_kernel(Path(root), languages=["python"])
    print("# PoC v2.1 — Dominant-text labeling")
    print()
    print(f"Root: `{root}`  |  Functions analyzed: {result.functions_analyzed}  |  Clusters: {len(result.clusters)}")
    print()
    print("| Cluster (param) | Scope | Members | Modal token | Shared stem | Varying alphabet |")
    print("|---|---|---|---|---|---|")
    for c in result.clusters:
        if c.verdict != "strong":
            continue
        names = [n for n, _, _ in c.members]
        label = label_cluster(names)
        modal = f"`{label['modal_token']}`×{label['modal_freq']}" if label['modal_token'] else "—"
        stem = ", ".join(f"`{t}`" for t in label["shared_stem"]) or "—"
        alpha = ", ".join(f"`{t}`" for t in label["varying_alphabet"][:6])
        if len(label["varying_alphabet"]) > 6:
            alpha += f" (+{len(label['varying_alphabet']) - 6})"
        if not alpha:
            alpha = "—"
        print(
            f"| `{c.parameter_name}` | `{c.scope}` | {len(names)} | "
            f"{modal} | {stem} | {alpha} |"
        )
    print()
    print("## Per-cluster detail")
    print()
    for c in result.clusters:
        if c.verdict != "strong":
            continue
        names = [n for n, _, _ in c.members]
        label = label_cluster(names)
        print(f"### `{c.parameter_name}` in `{c.scope}` ({len(names)} fns)")
        print()
        print(f"- Modal token: `{label['modal_token']}` (×{label['modal_freq']})")
        print(f"- Shared stem: {', '.join(f'`{t}`' for t in label['shared_stem']) or '_none_'}")
        print(f"- Varying alphabet: {', '.join(f'`{t}`' for t in label['varying_alphabet']) or '_none_'}")
        print(f"- Top tokens: {label['freq']}")
        print(f"- Members: {', '.join(f'`{n}`' for n in names)}")
        print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
